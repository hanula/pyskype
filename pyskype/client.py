

import os
import sys
import traceback
import gobject
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import logging

log = logging.getLogger(__name__)


DEBUG = True

class Notify(dbus.service.Object):
    def __init__(self, bus, callback):
        self.callback = callback
        dbus.service.Object.__init__(self, bus, '/com/Skype/Client', bus_name='com.Skype.API')


    @dbus.service.method(dbus_interface='com.Skype.API.Client')
    def Notify(self, message_text):
        self.callback(message_text)




class SkypeObject(object):
    ident = None
    properties = ()

    def __init__(self, skype, id):
        self.id = id
        self.skype = skype

        assert self.ident
        
        for property in self.properties:
            cmd = 'GET %s %s %s' % (self.ident, self.id, property)
            result = skype.send_command(cmd).encode('utf8')
            r = result.split(' ', 3)[3]
            setattr(self, property.lower(), r)


class User(SkypeObject):
    ident = 'USER'
    properties = (
        'HANDLE',
        'FULLNAME',
    )
    
class Chat(SkypeObject):
    ident = 'CHAT'
    properties = (
        'NAME',
        'TIMESTAMP',
        'ADDER',
        'STATUS',
        'MEMBERS',
        'TOPIC',
    )
    # Statuses
    DIALOG = 'DIALOG'
    MULTI_SUBSCRIBED = 'MULTI_SUBSCRIBED'

    def __repr__(self):
        return 'Chat(%s, %s, %s)' % (self.name, self.status, self.timestamp)

class ChatMessage(SkypeObject):
    ident = 'CHATMESSAGE'
    properties = (
        'BODY',
        'TYPE',
        'CHATNAME',
        'FROM_HANDLE',
        'TIMESTAMP',
        'STATUS',
        'ROLE',
    )

    # Statuses
    SAID = 'SAID'
    RECEIVED = 'RECEIVED'
    SENT = 'SENT'
    READ = 'READ'

    @property
    def is_incomming(self):
        return self.status.upper() in ('READ', 'RECEIVED')
        
    @property
    def is_direct(self):
        return self.chat.status == Chat.DIALOG
        
    @property
    def chat(self):
        return Chat(self.skype, self.chatname)

    def __repr__(self):
        return 'ChatMessage(%s, %s, %s, %s)' % (self.from_handle, self.type, self.status, self.timestamp)
        
    def reply(self, text):
        self.skype.send_command('CHATMESSAGE %s %s' % (self.chatname, text))

class SkypeClient(object):
    def __init__(self):
        self.verbose = False
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        try:
            self.connection = self.bus.get_object('com.Skype.API', '/com/Skype')
        except dbus.exceptions.DBusException, e:
            
            self.on_connection_failed()
            raise e
                
        self.notify = Notify(self.bus, self.notify)
        self.on_connection_made()
        
        self.send_command('NAME skype')
        self.send_command('PROTOCOL 7')
        
        user_handle = self.send_command('GET CURRENTUSERHANDLE').split(' ', 1)[1]
        self.user = User(self, user_handle)
        self.messages = []
        
    def get_status(self):
        ret = self.send_command('GET PROFILE RICH_MOOD_TEXT')
        return ret.replace('PROFILE RICH_MOOD_TEXT ','')

    def set_status(self, status):
        self.send_command('SET PROFILE RICH_MOOD_TEXT ' + status)

    def send_command(self, command):
        result = self.connection.Invoke(command)
        if self.verbose:
            print "-->", command
            print "<--", result
        return result

    
    def notify(self, command):
        
        try:
            args = command.split()
            
            if len(args) == 4 and (args[0], args[2]) == ('CHATMESSAGE', 'STATUS'):
                #if args[3] in ('RECEIVED', 'SENT'):
                msg_id = args[1]
                message = ChatMessage(self, msg_id)
                self.on_message(message)
        except Exception, e:
            print
            print '#' * 40
            print "Internal Error:", repr(e)
            print '#' * 40
        
        if self.verbose:
            print "<--", command

    def start(self):
        loop = gobject.MainLoop()
        loop.run()


    def on_message(self, message):
        
        for stored_message in self.messages:
            if message.id == stored_message.id:
                return
        
        self.messages = self.messages[-50:]
        self.messages.append(message)
        
        if message.status in (ChatMessage.RECEIVED, ChatMessage.READ):
            self.on_message_received(message)
            
        elif message.status == ChatMessage.SENT:
            self.on_message_sent(message)
        elif message.status == ChatMessage.READ:
            self.on_message_read(message)
        elif DEBUG:
            log.debug("Unknown message: %s" % message)


    ## Callbacks
    
    # Connection
    def on_connection_failed(self):
        pass
        
    def on_connection_made(self):
        pass
    
    # Message
    def on_message_received(self, message):
        pass

    def on_message_sent(self, message):
        pass

    def on_message_read(self, message):
        pass
        
    
if __name__ == '__main__':
    skype = SkypeClient()
    
    print skype.user.handle
    print skype.user.fullname


