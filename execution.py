"""Functions for executing third-party apps.
"""

import sys
import os
import webbrowser

if sys.platform == 'win32':
    
    import win32api
    
    def open_file(filename):
        if not os.path.isfile(filename):
            msg = 'File %s not found.' % filename
            raise Exception(msg)
        os.startfile(filename)
    
    def kill(pid):
        handle = win32api.OpenProcess(1, False, pid)
        win32api.TerminateProcess(handle, -1)
        win32api.CloseHandle(handle)

elif os.name == 'posix':
    
    import mimetypes
    import mailcap
    import signal
    
    def open_file(filename):
        if not os.path.isfile(filename):
            msg = 'File %s not found.' % filename
            raise Exception(msg)
        
        # Add mime types that may not be officially recognized
        mimetypes.add_type('text/csv', '.csv', strict=False)
        
        mime_type = mimetypes.guess_type(filename, strict=0)[0]
        if not mime_type:
            raise Exception(
                'File type has no association. Check your mailcap file.'
                )
        cap = mailcap.findmatch(
            mailcap.getcaps(),
            mime_type,
            filename="'%s'" % (filename)
            )
        command = cap[0]
        os.system(command + ' &')
    
    def kill(pid):
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, os.P_NOWAIT)

else:
    
    def open_file(filename):
        raise Exception('Opening third-party applications is not supported.')

def open_url(url):
    webbrowser.open(url)
