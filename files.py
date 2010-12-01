"""Routines to aid in file operations.

The file-locking code was adapted from Jonathan Feinberg's code
in the Python Cookbook.
"""

import sys
import os
import cPickle as pickle
import tempfile

if os.name == 'posix':
    # Unix
    USER_DIR = os.environ['HOME']
    if os.environ.has_key('XDG_DATA_HOME'):
        APP_CONF_DIR = os.environ['XDG_DATA_HOME']
    else:
        APP_CONF_DIR = os.path.join(os.environ['HOME'], '.config')
    SYS_CONF_DIR = '/etc'
    DIR_SEPARATOR = '/'
    
    import fcntl as __fcntl
    
    def __lock_shared(file):
        __fcntl.flock(file.fileno(), __fcntl.LOCK_SH)
    
    def __lock_exclusive(file):
        __fcntl.flock(file.fileno(), __fcntl.LOCK_EX)
    
    def __unlock(file):
        __fcntl.flock(file.fileno(), __fcntl.LOCK_UN)

elif sys.platform == 'win32' and os.environ.has_key('APPDATA'):
    # Windows NT, 2000, XP
    USER_DIR = os.environ['USERPROFILE']
    APP_CONF_DIR =  os.environ['APPDATA']
    SYS_CONF_DIR = os.path.join(os.environ['WINDIR'], 'Application Data')
    DIR_SEPARATOR = '\\'
    
    import win32con as __win32con
    import win32file as __win32file
    import pywintypes as __pywintypes
    __overlapped = __pywintypes.OVERLAPPED()
    
    def __lock_shared(file):
        file_handle = __win32file._get_osfhandle(file.fileno())
        __win32file.LockFileEx(file_handle, 0, 0, -65536, __overlapped)
    
    def __lock_exclusive(file):
        file_handle = __win32file._get_osfhandle(file.fileno())
        __win32file.LockFileEx(
            file_handle,
            __win32con.LOCKFILE_EXCLUSIVE_LOCK,
            0,
            -65536,
            __overlapped
            )
    
    def __unlock(file):
        hfile = __win32file._get_osfhandle(file.fileno())
        __win32file.UnlockFileEx(hfile, 0, -65536, __overlapped)
        

else:
    raise Exception('Not a supported platform.')

def save(data, filename, mode=0600, safe=False):
    """Save string data to a file using exclusive locking.
    
    If the safe arg is True (and this is a POSIX system), then
    this function will take every precaution possible to make sure
    the file is kept in a usable state in the event of a sudden application,
    operating system, or computer failure. This is wise to use when
    updating an important persistent file (a user or system configuration
    file, for instance). This is not necessary when writing a temp file or
    similar unimportant file.
    """
    if safe == True and (os.name != 'posix' or not os.path.exists(filename)):
        # The safe writing strategy is for POSIX systems only, and
        # is also not needed for newly created files.
        safe = False
    base = os.path.split(filename)[0]
    if not (base == '' or os.path.exists(base)):
        os.makedirs(base)
    try:
        if safe:
            fileno, tempname = tempfile.mkstemp(dir=base)
            f = os.fdopen(fileno, 'wb')
        else:
            f = open(filename, 'wb')
            os.chmod(filename, mode)
        __lock_exclusive(f)
        repr(data)
        f.write(data)
    finally:
        if vars().has_key('f'):
            if safe:
                f.flush()
                os.fsync(fileno)
            __unlock(f)
            f.close()
    if safe:
        os.rename(tempname, filename)

def load(filename):
    """Retrieve a string from a file using shared locking.
    """
    try:
        f = open(filename, 'rb')
        __lock_shared(f)
        data = f.read()
    finally:
        if vars().has_key('f'):
            __unlock(f)
            f.close()
    return data

def yield_lines(filename):
    """Yield a generator that iterates over each line of a file.
    """
    try:
        f = open(filename, 'rb')
        __lock_shared(f)
        for line in f:
            yield line
    finally:
        if vars().has_key('f'):
            __unlock(f)
            f.close()

def append(data, filename):
    """Add data to the end of a file.
    """
    base = os.path.split(filename)[0]
    if not (base == '' or os.path.exists(base)):
        os.makedirs(base)
    try:
        f = open(filename, 'ab')
        __lock_exclusive(f)
        f.write(data)
    finally:
        if vars().has_key('f'):
            __unlock(f)
            f.close()

def save_object(obj, file_name, mode=0600, safe=False):
    """Serialize an object and save it to a file.
    
    See the save() function above for information of the safe argument.
    """
    data = pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)
    save(data, file_name, mode, safe)

def load_object(filename):
    """Retrieve a saved object from a file.
    
    The object must be saved in the format used by the save_object() method
    elsewhere in this module.
    """
    return pickle.loads(load(filename))

def normpath(path):
    """Normalizes a path and identifies absolute directories.
    
    Follows the same rules as os.path.normath(), but also adds a trailing
    separator if the path can be determined to be directory.
    """
    path = os.path.normpath(path)
    if os.path.isdir(path):
        path += DIR_SEPARATOR
    return path
