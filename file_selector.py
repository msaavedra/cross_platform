"""Code to create simple file save and file open dialog boxes.
"""

import os
import sys
from cross_platform.files import USER_DIR

if os.name == 'posix':
    
    import gtk
    
    def _Filter(name, *patterns):
        filter = gtk.FileFilter()
        filter.set_name(name)
        for pattern in patterns:
            filter.add_pattern(pattern)
        return filter
    
    class FileDialog(object):
        
        def __init__(self, action, title=None, file_name='', dir=USER_DIR):
            """
            """
            dialog = gtk.FileChooserDialog()
            dialog.set_default_response(gtk.RESPONSE_OK)
            dialog.set_current_folder(dir)
            dialog.set_filename(file_name)
            
            action = action.title()
            if action == 'Open':
                dialog.set_action(gtk.FILE_CHOOSER_ACTION_OPEN)
                dialog.add_buttons(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OPEN, gtk.RESPONSE_OK
                    )
            elif action == 'Save':
                dialog.set_action(gtk.FILE_CHOOSER_ACTION_SAVE)
                dialog.add_buttons(
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_SAVE, gtk.RESPONSE_OK
                    )
                dialog.set_current_name(os.path.split(file_name)[1])
            else:
                raise Exception('Dialog type must be either "open" or "save".')
            
            if title:
                dialog.set_title(title)
            else:
                dialog.set_title('%s File' % action)
            
            
            file_name_parts = file_name.split('.', 1)
            if len(file_name_parts) > 1:
                extension = file_name_parts[1]
                filter = _Filter('.%s Files' % extension.upper())
                filter.add_pattern('*.%s' % extension)
                dialog.add_filter(filter)
            dialog.add_filter(_Filter('All Files', '*'))
            
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                self.file_name = dialog.get_filename()
                self.canceled = False
            else:
                self.file_name = ''
                self.canceled = True
            dialog.destroy()
            while gtk.events_pending():
                gtk.main_iteration()

elif sys.platform == 'win32' and os.environ.has_key('APPDATA'):
    
    import win32gui
    import win32con
    import pywintypes
    
    class FileDialog(object):
        
        def __init__(self, action, title=None, file_name='', dir=USER_DIR):
            
            self.canceled = False
            action = action.title()
            if action == 'Open':
                dialog_func = win32gui.GetOpenFileNameW
            elif action == 'Save':
                dialog_func = win32gui.GetSaveFileNameW
            else:
                raise Exception('Dialog type must be either "open" or "save".')
            
            if not title:
                title = '%s File' % action
            
            file_name_parts = file_name.split('.', 1)
            if len(file_name_parts) > 1:
                extension = file_name_parts[1]
                filter = '.%s Files\0*.%s\0' % (extension.upper(), extension)
                filter_index = 1
            else:
                extension = ''
                filter = None
                filter_index = 0
            
            try:
                self.file_name, custom_filter, flags = dialog_func(
                    InitialDir=dir,
                    Flags=win32con.OFN_HIDEREADONLY,
                    File=file_name,
                    DefExt=extension,
                    Title=title,
                    Filter=filter,
                    CustomFilter='All Files\0*\0',
                    FilterIndex=filter_index
                    )
            except pywintypes.error, reason:
                code = reason[0]
                if code == 0:
                    self.canceled = True
                    self.file_name = ''
                else:
                    raise pywintypes(reason)
            
            if '\0' in self.file_name:
                self.file_name = self.file_name.split('\0')[0]

else:
    raise Exception('IPC not supported on this platform.')

def __run():
    open_dialog = FileDialog('open')
    if open_dialog.canceled:
        print 'Canceled.'
        return
    print open_dialog.file_name
    save_dialog = FileDialog('save', file_name=open_dialog.file_name)
    if save_dialog.canceled:
        print 'Canceled.'
        return
    print save_dialog.file_name

if __name__ == '__main__':
    __run()
