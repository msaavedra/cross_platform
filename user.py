import os
import sys

if os.name == 'posix':
    
    import pwd
    import pexpect
    
    def authenticates(user, password):
        __check_user(user)
        if os.getuid() == 0:
            command = "su '%s' -c \"su '%s' -s /bin/true\"" % (user, user)
        else:
            command = "su '%s' -c /bin/true" % user
        child = pexpect.spawn(command)
        child.expect('Password:')
        child.sendline(password)
        child.readlines()
        child.close()
        if child.exitstatus == 0:
            return True
        else:
            return False
    
    def set_password(user, new_pw, old_pw=None, admin_pw=None):
        __check_user(user)
        if os.getuid() == 0:
            child = pexpect.spawn("passwd '%s'" % user)
        elif super_pw and not old_pw:
            print "su root -c \"passwd '%s'\"" % user
            child = pexpect.spawn("su root -c \"passwd '%s'\"" % user)
            child.expect('Password:')
            child.sendline(admin_pw)
        elif old_pw and not admin_pw:
            child = pexpect.spawn("su '%s' -c passwd" % user)
            child.expect('Password:')
            child.sendline(old_pw)
            child.expect('UNIX password:')
            child.sendline(old_pw)
        else:
            raise Exception()
        
        answer = child.expect(['su: incorrect password','New UNIX password:'])
        if answer == 0:
            child.close()
            raise Exception('Permission denied, incorrect authentication.')
        child.sendline(new_pw)
        answer = child.expect(['BAD PASSWORD:','Retype new UNIX password:'])
        if answer == 0:
            msg = 'Bad Password -- %s.' % child.readline().strip()
            child.close()
            raise Exception(msg)
        child.sendline(new_pw)
        child.close()
        if child.exitstatus != 0:
            msg = 'Password change failed. Error %d.' % child.exitstatus
            raise Exception(msg)
    
    def create(user, admin_pw=None):
        for char in ('/', '\\', '|', '&', ';', '*', '"', "'"):
            if char in user:
                raise Exception('User %s contains invalid characters.' % user)
        if os.getuid() == 0:
            child = pexpect.spawn("useradd '%s'" % user)
        elif admin_pw:
            child = pexpect.spawn('su - -c "useradd \'%s\'"' % user)
            child.expect('Password:')
            child.sendline(admin_pw)
        else:
            raise Exception()
        msg = ' '.join(child.readlines()).split(':')[-1].strip()
        child.close()
        if child.exitstatus != 0:
            raise Exception('User creation failed -- %s.' % msg)
    
    def delete(user, admin_pw=None):
        __check_user(user)
        if os.getuid() == 0:
            child = pexpect.spawn("userdel '%s'" % user)
        elif admin_pw:
            child = pexpect.spawn('su - -c "userdel \'%s\'"' % user)
            child.expect('Password:')
            child.sendline(admin_pw)
        else:
            raise Exception()
        msg = ' '.join(child.readlines()).split(':')[-1].strip()
        child.close()
        if child.exitstatus != 0:
            raise Exception('User deletion failed -- %s.' % msg)
    
    def activate(user, admin_pw=None):
        __check_user(user)
        if os.getuid() == 0:
            child = pexpect.spawn("usermod -U '%s'" % user)
        elif admin_pw:
            child = pexpect.spawn('su - -c "usermod -U \'%s\'"' % user)
            child.expect('Password:')
            child.sendline(admin_pw)
        else:
            raise Exception()
        msg = ' '.join(child.readlines()).split(':')[-1].strip()
        child.close()
        if child.exitstatus != 0:
            raise Exception('User suspension failed -- %s.' % msg)
    
    def suspend(user, admin_pw=None):
        __check_user(user)
        if os.getuid() == 0:
            child = pexpect.spawn("usermod -L '%s'" % user)
        elif admin_pw:
            child = pexpect.spawn('su - -c "usermod -L \'%s\'"' % user)
            child.expect('Password:')
            child.sendline(admin_pw)
        else:
            raise Exception()
        msg = ' '.join(child.readlines()).split(':')[-1].strip()
        child.close()
        if child.exitstatus != 0:
            raise Exception('User suspension failed -- %s.' % msg)
    
    def __check_user(user):
        try:
            pwd.getpwnam(user) # Does this work with kerberos, etc?
        except:
            raise Exception('Invalid user: %s' % user)

elif sys.platform == 'win32' and os.environ.has_key('APPDATA'):
    
    import win32security
    
    def authenticates(user, password):
        try:
            token = win32security.LogonUser(
                user,
                None,
                password,
                win32security.LOGON32_LOGON_NETWORK,
                win32security.LOGON32_PROVIDER_DEFAULT
                )
        except win32security.error:
            return False
        
        if token:
            return True
        else:
            return False
    
    def set_password(user, new_pw, old_pw=None, admin_pw=None):
        raise Exception('Not implemented yet.')
    
    def create(user, admin_pw=None):
        raise Exception('Not implemented yet.')
    
    def delete(user, admin_pw=None):
        raise Exception('Not implemented yet.')
    
    def activate(user, admin_pw=None):
        raise Exception('Not implemented yet.')
    
    def suspend(user, admin_pw=None):
        raise Exception('Not implemented yet.')
    
else:
    raise Exception('Authentication not supported on this platform.')
