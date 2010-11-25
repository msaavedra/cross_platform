"""This module implements a simple API for inter-process communication.

It uses unix domain sockets for posix-compatible systems, and named pipes
for win32 systems.
"""

import os
import sys
import thread
import time
import cPickle as pickle

BUFFER_SIZE = 4096
TIMEOUT = 30 #seconds

class Error(Exception): pass

class TimeoutError(Error): pass

class DisconnectError(Error): pass

class _IterableConnection(object):
    """A small base class to improve use of iterables in Connection objects.
    """
    def xread(self, timeout=10):
        """An iterable version of the read() method.
        
        This is a generator function that retrieves one object at a
        time across the IPC connection, allowing efficient handling of
        passing iterables through the connection.
        """
        while True:
            item = self.read(timeout)
            if isinstance(item, StopIteration):
                raise item
            else:
                yield item
    
    def xwrite(self, items):
        """An iterable version of the write() method.
        
        This method takes an iterable (list, tuple, generator, etc.) and
        sends it across the IPC connection one item at a time.
        """
        for item in items:
            self.write(item)
        self.write(StopIteration())

if os.name == 'posix':
    
    import socket
    import select
    
    def listen(filename, handler):
        """Begin listening on the specified socket file.
        
        This will block until it receives data, whereupon it will 
        start a new thread to handle the incoming connection, then 
        block again. It will never return, so the thread in which
        it is called should be considered permanently occupied.
        """
        if os.path.exists(filename):
            os.remove(filename)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(filename)
        # Allow everyone to write. Other permissions don't matter on sockets.
        os.chmod(filename, 0622)
        sock.listen(5)
        while True:
            conn, client = sock.accept()
            conn.setblocking(0)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            connection = Connection(conn)
            thread.start_new_thread(handler, (connection,))
    
    def connect(filename, timeout=10):
        """Make a new open connection object to an IPC server.
        
        This is a client-side factory function for the Connection class.
        """
        socket_obj = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_obj.setblocking(0)
        socket_obj.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        start = time.time()
        while True:
            try:
                socket_obj.connect(filename)
            except socket.error, msg:
                if msg[0] == 111:
                    if time.time() < (start + timeout):
                        time.sleep(1)
                        continue
                if msg[0] != 115:
                    raise Error(msg)
            else:
                break
        return Connection(socket_obj)
    
    class Connection(_IterableConnection):
        
        def __init__(self, unix_domain_socket):
            self._socket = unix_domain_socket
            self.open = True
        
        def read(self, timeout=10):
            """Receive a complete message from a socket connection.
            """
            read_buffer = ''
            while '-' not in read_buffer:
                incoming = self._recv(2, timeout)
                read_buffer += incoming
            msg_length, read_buffer = read_buffer.split('-', 1)
            msg_length = int(msg_length)
            received = len(read_buffer)
            while received < msg_length:
                incoming = self._recv(msg_length - received)
                received += len(incoming)
                read_buffer += incoming
            return pickle.loads(read_buffer)
        
        def write(self, item):
            """Send a complete message through a socket connection.
            """
            message = pickle.dumps(item)
            message = '%d-%s' % (len(message), message)
            msg_length = len(message)
            offset = 0
            while msg_length > offset:
                try:
                    sock_lists = select.select(
                        [self._socket], [self._socket], [], 10
                        )
                    sent = sock_lists[1][0].send(message[offset:])
                    offset += sent
                except IndexError:
                    raise TimeoutError()
                except socket.error, reason:
                    if 'Broken pipe' in reason:
                        raise DisconnectError()
                    else:
                        raise Error(reason)
        
        def is_readable(self):
            readable, writable, errs = select.select([self._socket], [], [], 0)
            return bool(readable)
        
        def close(self):
            self._socket.close()
            self.open = False
        
        def __del__(self):
            if self.open:
                self.close()
        
        def _recv(self, size, timeout=2):
            """Receive a chunk of data of the specified size in bytes.
            
            This is a private method, not part of the API. It is subject to
            change without notice and should not be used directly.
            """
            try:
                sock_lists = select.select([self._socket], [], [], timeout)
                incoming = sock_lists[0][0].recv(size)
            except IndexError:
                raise TimeoutError()
            except socket.error:
                raise DisconnectError()
            if incoming == '':
                raise DisconnectError()
            return incoming

elif sys.platform == 'win32' and os.environ.has_key('APPDATA'):
    
    import time
    import pywintypes
    
    from win32pipe import *
    from win32file import *
    from win32api import GetLastError
    from winerror import ERROR_MORE_DATA
    
    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
    
    def listen(filename, handler):
        """Begin listening on the specified named pipe file.
        
        This will wait until it receives data, whereupon it will 
        start a new thread to handle the incoming connection, then 
        wait again. It will never return, so the thread in which
        it is called should be considered permanently occupied.
        """
        pipe = CreateNamedPipe(
            filename,
            PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE,
            PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            BUFFER_SIZE,
            BUFFER_SIZE,
            TIMEOUT * 1000,
            None
            )
        if pipe == INVALID_HANDLE_VALUE:
            raise Error('Error creating communication file.')
        while True:
            connection = Connection(pipe)
            exit_code = ConnectNamedPipe(pipe, None)
            if exit_code == 0:
                thread.start_new_thread(handler, (connection,))
            else:
                CloseHandle(pipe)
                msg = 'Error %s connecting to named pipe.' % exit_code
                raise Error(msg)
            # Create a new pipe handler to replace the used one.
            pipe = CreateNamedPipe(
                filename,
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
                PIPE_UNLIMITED_INSTANCES,
                BUFFER_SIZE,
                BUFFER_SIZE,
                TIMEOUT * 1000,
                None
                )
            if pipe == INVALID_HANDLE_VALUE:
                raise Error('Error creating communication file.')
        
    def connect(filename):
        """Make a new open connection object to an IPC server.
        
        This is a client-side factory function for the Connection class.
        """
        while True:
            pipe = CreateFile( 
                filename, GENERIC_READ | GENERIC_WRITE, 
                0, None, OPEN_EXISTING, 0, None
                )
            
            if pipe != INVALID_HANDLE_VALUE:
                break
            
            WaitNamedPipe(filename, TIMEOUT * 1000)
        return Connection(pipe)
    
    class Connection(_IterableConnection):
        
        def __init__(self, pipe):
            self._pipe = pipe
            self.open = True
        
        def read(self, timeout=10):
            start_time = time.time()
            while True:
                if (time.time() - start_time) > timeout:
                    raise TimeoutError()
                try:
                    peek, read, waiting = PeekNamedPipe(self._pipe, 2)
                except pywintypes.error, reason:
                    if 'Broken pipe' in reason:
                        raise DisconnectError()
                    else:
                        raise Error(reason)
                if read > 0:
                    break
                else:
                    time.sleep(.01) # Don't eat all the CPU time in this loop.
            
            read_buffer = ''
            while '-' not in read_buffer:
                exit_code, incoming = ReadFile(self._pipe, 2)
                read_buffer += incoming
            msg_length, read_buffer = read_buffer.split('-', 1)
            msg_length = int(msg_length)
            received = len(read_buffer)
            while received < msg_length:
                exit_code, incoming = ReadFile(self._pipe, msg_length)
                received += len(incoming)
                read_buffer += incoming
            return pickle.loads(read_buffer)
        
        def write(self, item):
            message = pickle.dumps(item)
            message = '%d-%s' % (len(message), message)
            try:
                exit_code, bytes_written = WriteFile(self._pipe, message)
            except pywintypes.error, reason:
                if 'Pipe not connected' in reason:
                    raise DisconnectError()
                else:
                    raise Error(reason)
        
        def is_readable(self):
            peek, read, waiting = PeekNamedPipe(self._pipe, 1)
            return (read > 0)
        
        def close(self):
            CloseHandle(self._pipe)
            self.open = False
        
        def __del__(self):
            if self.open:
                self.close()

else:
    raise Error('IPC not supported on this platform.')


def test_server():
    def echo(connection):
        print 'Connected to pipe in new thread.'
        for item in connection.xread():
            print item
        connection.write('received iterable.')
        connection.close()
    listen(r'\\.\pipe\test.pipe', echo)

def test_client():
    msg = xrange(20)
    connection = connect(r'\\.\pipe\test.pipe')
    connection.xwrite(msg)
    item = connection.read()
    print 'server replied:', item
    connection.close()
