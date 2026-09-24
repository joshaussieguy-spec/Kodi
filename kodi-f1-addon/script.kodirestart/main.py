# Restart Kodi - v1.0.0
# Restarts Kodi via the XBMC.RestartApp built-in.
# Runs INSIDE the current Kodi session, so the restart is visible
# on the real display (no SSH phantom-session problem).
import xbmcgui

RESTART_MSG = 'Restarting Kodi...'

def main():
    xbmcgui.Dialog().notification('Restart Kodi', RESTART_MSG, xbmcgui.NOTIFICATION_INFO, 2000)
    # Small delay so the notification paints before the app tears down
    import xbmc
    xbmc.sleep(1500)
    xbmc.executebuiltin('XBMC.RestartApp')

if __name__ == '__main__':
    main()