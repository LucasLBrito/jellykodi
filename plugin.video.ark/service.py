# -*- coding: utf-8 -*-
"""
Serviço JellyKodi: roda em segundo plano enquanto o Kodi está aberto.

- "Pular abertura/resumo": pelos capítulos do MKV (Intro, Opening, Abertura, OP, Recap...)
  ou pela marcação manual salva para a pasta (botão L3 do controle, duas vezes).
- "Próximo episódio": nos créditos (capítulo Credits/Ending/ED, marcação R3 por pasta,
  ou últimos segundos de arquivos com cara de episódio), com contagem regressiva.
- Histórico para a fileira "Continuar assistindo" e retomada automática sem perguntar.
"""
import json
import os
import time

import xbmc
import xbmcgui

from resources.lib import jk_common as C
from resources.lib import jk_meta as M
from resources.lib import jk_organize as O
from resources.lib.jk_dialog import OverlayButton

# segundos que a pasta precisa ficar parada antes de mexer (download/cópia terminando)
ESPERA_ESTAVEL = 30


class Session(object):
    """Estado do vídeo que está tocando agora."""

    def __init__(self, path, total):
        self.path = path
        self.folder = C.split_path(path)[0]
        self.total = total
        self.pos = 0.0
        self.dismissed = set()      # segmentos que o usuário já pulou/dispensou
        self.next_path = None       # próximo episódio (quando os créditos começarem)
        self.next_checked = False
        self.next_cancelled = False
        self.go_next = False        # vai tocar o próximo ao terminar
        self.mark_start = None      # marcação manual da abertura em andamento
        self.last_save = time.time()


class JKPlayer(xbmc.Player):
    def __init__(self, service):
        super(JKPlayer, self).__init__()
        self.service = service

    def onAVStarted(self):
        self.service.on_start()

    def onPlayBackStopped(self):
        self.service.on_stop(ended=False)

    def onPlayBackEnded(self):
        self.service.on_stop(ended=True)

    def onPlayBackError(self):
        self.service.on_stop(ended=False)


class Service(xbmc.Monitor):
    def __init__(self):
        super(Service, self).__init__()
        self.player = JKPlayer(self)
        self.sess = None
        self.dialog = None
        self.dialog_kind = None     # 'skip' | 'next'
        self.dialog_seg = None
        self.countdown_end = 0
        self.state = C.load_state()
        self.pending_bump = 0.0   # recarregar as fileiras só depois que o Kodi parar de mexer na biblioteca
        self.org_sig = None       # retrato da pasta vigiada pelo organizador automático
        self.org_desde = 0.0

    # ------------------------------------------------------------ eventos do Kodi
    def onSettingsChanged(self):
        C.ADDON = C.xbmcaddon.Addon(C.ADDON_ID)

    def onNotification(self, sender, method, data):
        # Vem do mapeamento do controle: NotifyAll(jellykodi,mark_intro)
        if method in ('VideoLibrary.OnScanFinished', 'VideoLibrary.OnUpdate') and sender == 'xbmc':
            # um OnUpdate por item: só anota, o laço principal recarrega uma vez no fim
            self.pending_bump = time.time()
            return
        if sender != 'jellykodi':
            return
        C.log('comando: %s' % method)
        if method.endswith('mark_intro'):
            self.mark_intro()
        elif method.endswith('mark_credits'):
            self.mark_credits()
        elif method.endswith('clear_marks'):
            self.clear_marks()

    def on_start(self):
        try:
            if not self.player.isPlayingVideo():
                return
            path = self.player.getPlayingFile()
            total = self.player.getTotalTime()
        except RuntimeError:
            return
        if self.sess and self.sess.path == path:
            return  # mesmo arquivo (ex.: troca de faixa de áudio): mantém o estado
        if self.sess:
            self.finish(self.sess, ended=self.sess.go_next)
        self.close_dialog()
        self.sess = Session(path, total)
        C.log('tocando %s (%.0fs)' % (path, total))

        # Retomada automática (vinda da fileira "Continuar assistindo")
        raw = C.HOME.getProperty('jk_seek')
        if raw:
            C.HOME.clearProperty('jk_seek')
            try:
                req = json.loads(raw)
                if req.get('path') == path and req.get('pos', 0) > 0:
                    self.player.seekTime(max(0.0, float(req['pos']) - C.setting_int('resume_rewind', 5)))
            except Exception as exc:
                C.log('seek falhou: %s' % exc, xbmc.LOGWARNING)

    def on_stop(self, ended):
        sess = self.sess
        # Ao trocar de episódio o Kodi pode avisar o "stop" do anterior depois que o novo já começou
        try:
            if sess and self.player.isPlayingVideo() and self.player.getPlayingFile() == sess.path:
                return
        except RuntimeError:
            pass
        self.sess = None
        self.close_dialog()
        if not sess:
            return
        self.finish(sess, ended)
        if ended and sess.go_next and sess.next_path and C.setting_bool('autoplay_next', True):
            C.log('próximo episódio: %s' % sess.next_path)
            xbmc.sleep(300)
            self.player.play(sess.next_path)

    def finish(self, sess, ended):
        total = sess.total or 1
        done = ended or (sess.pos / total) >= 0.92 or (total - sess.pos) < 60
        self.state = C.load_state()
        self.state['history'][sess.path] = {
            'pos': 0 if done else round(sess.pos, 1),
            'total': round(total, 1),
            'ts': time.time(),
            'done': bool(done),
        }
        C.save_state(self.state)
        C.bump_widgets()

    # ------------------------------------------------------------ laço principal
    def auto_metadata(self):
        """Pastas novas: detecta filmes/séries e manda o Kodi buscar sinopse/capas na internet."""
        if not C.setting_bool('auto_scrape', True):
            return
        try:
            st = C.load_state()
            if not st.get('player_defaults_v17c'):
                # estilo Netflix: retoma de onde parou sem perguntar "Retomar de..."
                M.rpc('Settings.SetSettingValue', setting='myvideos.selectaction', value=2)
                # direcional no vídeo: avança na hora, sem os 750 ms de espera do padrão
                M.rpc('Settings.SetSettingValue', setting='videoplayer.seekdelay', value=0)
                # não abrir cada MKV só para tirar um quadro de miniatura: é lento e gera
                # as miniaturas image://video@, que travam a navegação
                M.rpc('Settings.SetSettingValue', setting='myvideos.extractthumb', value=False)
                M.rpc('Settings.SetSettingValue', setting='myvideos.extractchapterthumbs', value=False)
                # Voltar já funciona no controle, então o item '..' só rouba o foco:
                # sem ele, ao abrir uma lista o foco cai direto no primeiro vídeo
                M.rpc('Settings.SetSettingValue', setting='filelists.showparentdiritems', value=False)
                # abrir uma série já posiciona no próximo episódio não assistido
                M.rpc('Settings.SetSettingValue', setting='videolibrary.tvshowsselectfirstunwatcheditem', value=2)
                st['player_defaults_v17c'] = True
            M.scrapers_to_portuguese(st)
            did = M.auto_configure(st)
            refresh = st.pop('needs_ptbr_refresh', False)
            C.save_state(st)
            if refresh and not xbmc.getCondVisibility('Library.IsScanning'):
                C.log('buscando de novo em português')
                M.refresh_all_ptbr()
            if did:
                kinds = {'movies': 'filmes', 'tvshows': 'séries', 'tvshow_single': 'série'}
                xbmcgui.Dialog().notification(
                    'JellyKodi', 'Buscando capas e sinopses: ' + ', '.join('%s (%s)' % (l, kinds[k]) for l, k in did),
                    time=6000, sound=False)
        except Exception as exc:
            C.log('auto_metadata: %s' % exc, xbmc.LOGWARNING)

    # ------------------------------------------------------------ organizar sozinho
    def auto_organize(self):
        """Arrastou uma pasta para o Downloads? organiza sem precisar apertar nada.

        Primeiro tira um retrato barato da pasta. Enquanto o retrato não muda, não há
        nada novo e nem olhamos o conteúdo. Quando muda, espera o retrato ficar parado
        por ESPERA_ESTAVEL segundos — é assim que se evita mexer num download pela metade.
        """
        if not C.setting_bool('auto_organize', True):
            return
        if self.player.isPlaying() or xbmc.getCondVisibility('Library.IsScanning'):
            return
        root = O.watch_root()
        if not root or not os.path.isdir(root):
            return
        sig = O.folder_signature(root)
        if sig is None:
            return
        if sig != self.org_sig:
            self.org_sig = sig
            self.org_desde = time.time()
            return
        if not self.org_desde or time.time() - self.org_desde < ESPERA_ESTAVEL:
            return
        self.org_desde = 0.0

        series_root, filmes_root = O.roots()
        if not series_root and not filmes_root:
            return
        try:
            plans = O.plan_folder(root, series_root, filmes_root)
        except Exception as exc:
            C.log('auto_organize (plano): %s' % exc, xbmc.LOGERROR)
            return
        if not plans:
            self.org_sig = O.folder_signature(root)
            return
        C.log('organizando sozinho: %d vídeo(s) em %s' % (len(plans), root))
        xbmcgui.Dialog().notification('JellyKodi', 'Organizando %d vídeo(s)...' % len(plans),
                                      time=4000, sound=False)
        try:
            movidos, _feitos = O.apply_moves(plans)
        except Exception as exc:
            C.log('auto_organize (mover): %s' % exc, xbmc.LOGERROR)
            self.org_sig = O.folder_signature(root)
            return
        self.org_sig = O.folder_signature(root)
        if not movidos:
            return
        linhas = O.resumo(plans, series_root, filmes_root)
        resumo_curto = ', '.join(l.replace('[B]', '').replace('[/B]', '').split(':')[0] for l in linhas[:2])
        st = C.load_state()
        M.auto_configure(st)
        C.save_state(st)
        M.scan()
        xbmcgui.Dialog().notification('JellyKodi', 'Pronto: %s (%d vídeos)' % (resumo_curto, movidos),
                                      time=6000, sound=False)
        C.bump_widgets()

    def run(self):
        C.log('serviço iniciado')
        next_meta = time.time() + 20  # espera o Kodi terminar de abrir
        next_org = time.time() + 10
        while not self.abortRequested():
            if self.pending_bump and time.time() - self.pending_bump > 5 \
                    and not xbmc.getCondVisibility('Library.IsScanning'):
                self.pending_bump = 0.0
                C.bump_widgets()
            if time.time() >= next_org:
                next_org = time.time() + 15
                try:
                    self.auto_organize()
                except Exception as exc:
                    C.log("auto_organize: %s" % exc, xbmc.LOGERROR)
            if time.time() >= next_meta and not self.player.isPlaying():
                next_meta = time.time() + 120
                self.auto_metadata()
            if self.sess and self.player.isPlayingVideo():
                try:
                    self.tick()
                except RuntimeError:
                    pass  # vídeo acabou no meio do tick
                except Exception as exc:  # nunca derrubar o serviço
                    C.log('erro: %s' % exc, xbmc.LOGERROR)
                if self.waitForAbort(0.5):
                    break
            else:
                if self.waitForAbort(1):
                    break
        self.close_dialog()

    def tick(self):
        s = self.sess
        t = self.player.getTime()
        total = self.player.getTotalTime() or s.total
        s.pos, s.total = t, total

        if time.time() - s.last_save > 30:  # salva progresso de tempos em tempos
            s.last_save = time.time()
            self.finish_partial(s)

        self.handle_dialog(s, t)

        if self.dialog is None:
            seg = self.skip_segment(s, t, total)
            if seg and seg['key'] not in s.dismissed:
                if C.setting_bool('auto_skip_intro', False):
                    s.dismissed.add(seg['key'])
                    self.player.seekTime(seg['end'])
                    xbmcgui.Dialog().notification('JellyKodi', '%s pulada' % seg['what'], time=2500, sound=False)
                else:
                    self.open_dialog('skip', seg, main=seg['label'])
                return
            if not s.next_cancelled and self.in_outro(s, t, total):
                if not s.next_checked:
                    s.next_checked = True
                    s.next_path = C.next_video(s.path)
                if s.next_path:
                    secs = C.setting_int('next_countdown', 10)
                    self.countdown_end = time.time() + secs
                    s.go_next = True
                    self.open_dialog('next', None,
                                     main='Próximo episódio em %d' % secs,
                                     second='Assistir créditos',
                                     info='A seguir: ' + C.nice_title(s.next_path))

    def finish_partial(self, s):
        st = C.load_state()
        st['history'][s.path] = {'pos': round(s.pos, 1), 'total': round(s.total, 1),
                                 'ts': time.time(), 'done': False}
        C.save_state(st)

    # ------------------------------------------------------------ detecção
    def chapter_bounds(self, total):
        """Retorna (indice_atual, nome, inicio_s, fim_s) do capítulo atual, ou None."""
        try:
            idx = int(xbmc.getInfoLabel('Player.Chapter') or 0)
            count = int(xbmc.getInfoLabel('Player.ChapterCount') or 0)
        except ValueError:
            return None
        if idx <= 0 or count <= 1:
            return None
        name = xbmc.getInfoLabel('Player.ChapterName')
        raw = xbmc.getInfoLabel('Player.Chapters')
        starts = {0.0}
        for tok in raw.split(','):
            try:
                starts.add(round(float(tok), 4))
            except ValueError:
                pass
        starts = sorted(starts)
        if idx > len(starts):
            return None
        start = starts[idx - 1] * total / 100.0
        end = starts[idx] * total / 100.0 if idx < len(starts) else total
        return idx, name, start, end

    def skip_segment(self, s, t, total):
        ch = self.chapter_bounds(total)
        if ch:
            idx, name, start, end = ch
            if INTRO(name) and end - t > 2:
                return {'key': ('ch', idx), 'end': end, 'label': 'Pular abertura', 'what': 'Abertura'}
            if C.RECAP_RE.search(name or '') and end - t > 2:
                return {'key': ('ch', idx), 'end': end, 'label': 'Pular resumo', 'what': 'Resumo'}
        mark = C.load_state_cached(self).get('intros', {}).get(s.folder)
        if mark and mark['start'] - 1 <= t < mark['end'] - 2:
            return {'key': ('mark', 0), 'end': mark['end'], 'label': 'Pular abertura', 'what': 'Abertura'}
        return None

    def in_outro(self, s, t, total):
        if total < 300:  # vídeos curtos: ignora
            return False
        ch = self.chapter_bounds(total)
        if ch and C.OUTRO_RE.search(ch[1] or '') and not INTRO(ch[1]):
            return True
        secs = C.load_state_cached(self).get('credits', {}).get(s.folder)
        if secs:
            return t >= total - secs
        fallback = C.setting_int('next_fallback', 30)
        if fallback > 0 and C.looks_like_episode(s.path):
            return t >= total - fallback
        return False

    # ------------------------------------------------------------ botão flutuante
    def open_dialog(self, kind, seg, main, second='', info=''):
        C.log('botão: %s (%s)' % (main, kind))
        self.dialog = OverlayButton.create(main_label=main, second_label=second, info_label=info)
        self.dialog_kind = kind
        self.dialog_seg = seg
        self.dialog.show()

    def close_dialog(self):
        if self.dialog is not None:
            try:
                self.dialog.close()
            except Exception:
                pass
        self.dialog = None
        self.dialog_kind = None
        self.dialog_seg = None

    def handle_dialog(self, s, t):
        if self.dialog is None:
            return
        res = self.dialog.result
        if self.dialog_kind == 'skip':
            seg = self.dialog_seg
            if res == 'main':
                s.dismissed.add(seg['key'])
                self.close_dialog()
                self.player.seekTime(seg['end'])
            elif res == 'dismiss' or t >= seg['end'] - 1:
                s.dismissed.add(seg['key'])
                self.close_dialog()
        elif self.dialog_kind == 'next':
            left = int(round(self.countdown_end - time.time()))
            if res == 'main' or (left <= 0 and C.setting_bool('autoplay_next', True)):
                nxt = s.next_path
                s.go_next = True
                self.close_dialog()
                self.finish(s, ended=True)
                self.sess = None
                self.player.play(nxt)
            elif res in ('second', 'dismiss'):
                s.next_cancelled = True
                s.go_next = res == 'dismiss'  # "voltar" = esconde, mas ainda toca o próximo no fim
                self.close_dialog()
            else:
                self.dialog.set_main_label('Próximo episódio em %d' % max(left, 0))

    # ------------------------------------------------------------ marcação manual
    def mark_intro(self):
        s = self.sess
        if not s:
            return
        t = self.player.getTime()
        if s.mark_start is None:
            s.mark_start = t
            xbmcgui.Dialog().notification('JellyKodi', 'Início da abertura marcado (%s). Aperte L3 de novo no fim.' % C.fmt_time(t), time=4000)
            return
        start, end = s.mark_start, t
        s.mark_start = None
        if end - start < 5:
            xbmcgui.Dialog().notification('JellyKodi', 'Marcação cancelada (muito curta).', time=3000)
            return
        st = C.load_state()
        st['intros'][s.folder] = {'start': round(start, 1), 'end': round(end, 1)}
        C.save_state(st)
        self._cache = None
        s.dismissed.add(('mark', 0))
        xbmcgui.Dialog().notification('JellyKodi', 'Abertura salva para esta pasta: %s a %s' % (C.fmt_time(start), C.fmt_time(end)), time=5000)

    def mark_credits(self):
        s = self.sess
        if not s:
            return
        t = self.player.getTime()
        st = C.load_state()
        st['credits'][s.folder] = round(s.total - t, 1)
        C.save_state(st)
        self._cache = None
        xbmcgui.Dialog().notification('JellyKodi', 'Créditos marcados: faltando %s em cada episódio desta pasta' % C.fmt_time(s.total - t), time=5000)

    def clear_marks(self):
        s = self.sess
        if not s:
            return
        st = C.load_state()
        st['intros'].pop(s.folder, None)
        st['credits'].pop(s.folder, None)
        C.save_state(st)
        self._cache = None
        xbmcgui.Dialog().notification('JellyKodi', 'Marcações desta pasta apagadas.', time=3000)


def INTRO(name):
    return bool(C.INTRO_RE.search(name or ''))


def _load_state_cached(service):
    """Lê o state.json no máximo a cada 5 s (o tick roda 2x por segundo)."""
    cache = getattr(service, '_cache', None)
    if cache is None or time.time() - cache[0] > 5:
        cache = (time.time(), C.load_state())
        service._cache = cache
    return cache[1]


C.load_state_cached = _load_state_cached

if __name__ == '__main__':
    Service().run()
