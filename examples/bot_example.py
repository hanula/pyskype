import sys
import getopt
from pyskype.client import SkypeClient, Chat

import threading
import requests

class SkypeBotPlugin(object):
    name = ''
    description = ''
    enabled = True
    activator_commands = None
    command_help = ''           # Help on plugin command
    additional_help = ''        # Additional help/usage text on plugin behavior
    
    def __init__(self, bot):
        self.bot = bot
        
    def on_message_received(self, message):
        pass
        
    def on_command(self, message, command, input):
        pass
        

class SkypeBot(SkypeClient):

    def __init__(self, call_name='bot'):
        super(SkypeBot, self).__init__()
        self.call_name = call_name
        self.verbose = True
        self.plugins = []
        
        for plugin_class in SkypeBotPlugin.__subclasses__():
            plugin = plugin_class(self)
            if not plugin.name:
                plugin.name = plugin_class.__name__
            self.plugins.append(plugin)

    @property
    def enabled_plugins(self):
        return [plugin for plugin in self.plugins if plugin.enabled]
     
    def execute_command(self, message, command, args):
        command = command.lower()
        for plugin in self.enabled_plugins:
            if command in plugin.activator_commands:
                plugin.on_command(message, command, args)
    
    
    def on_connection_made(self):
        print "Connected"
    
    def on_message_sent(self, message):
        print "SENT", self.user.handle, message.from_handle, message
        #if self.user.handle != message.from_handle:
        self.on_bot_message(message)
    
    def on_message_received(self, message):
        print "RECEIVED", self.user.handle, message.from_handle, message
        #if self.user.handle != message.from_handle:
        self.on_bot_message(message)
    
    def on_bot_message(self, message):
        
        if message.type == 'SAID':
            for plugin in self.enabled_plugins:
                plugin.on_message_received(message)
            
            text = message.body.strip()
            
            # If it's not direct message then check if it's a valid bot call command
            if not message.is_direct:
                call_cmd = self.call_name + ' '
                
                if text.lower().startswith(call_cmd.lower()):
                    text = text[len(call_cmd):].strip()
                else:
                    return
                    
            if text:
                if ' ' in text:
                    cmd, input = text.split(' ', 1)
                else:
                    cmd, input = text, ''
                
                self.execute_command(message, cmd, input)
            


    def fetch_url(self, url, **kwargs):
        pass
        
class EchoPlugin(SkypeBotPlugin):
    activator_commands = ['echo']
    
    def on_command(self, message, command, input):
        if input:
            message.reply(input)
        
        
from BeautifulSoup import BeautifulSoup
class WikipediaPlugin(SkypeBotPlugin):
    activator_commands = ['wiki', 'wikipedia']
    

    def on_command(self, message, command, input):
        
        data = requests.get('http://en.wikipedia.org/w/api.php?action=opensearch', params={'search': input.strip()})
        
        data = json.loads(data.content)
        
        titles = data[1]
        if not titles:
            message.reply('Not found')
        else:
            title = titles[0]   # Best match
        
            data = requests.get('http://en.wikipedia.org/w/api.php?action=parse&prop=text&format=json', params={'page': title, 'redirects': ''})
            data = json.loads(data.content)
            text = data['parse']['text']['*']
            
            soup = BeautifulSoup(text, convertEntities=BeautifulSoup.HTML_ENTITIES)
            garbage = soup.find('table')
            if garbage:
                garbage.extract()
            #paragraphs = soup.findAll('p', limit=2)
            summary = soup.find('p')

            for spam in summary.findAll(style=lambda style:style and 'display:none' in style.lower().replace(' ','')):
                spam.extract()
            
            summary = u''.join([c for c in summary.recursiveChildGenerator() if isinstance(c, unicode)])
            # remove all unicode symbols and markup 
            summary = re.sub(r'&#\d+;', u'', summary)
            summary = re.sub(r'\[\d+\]', u'', summary)
            
            summary += '\n' + 'http://en.wikipedia.org/wiki/' + title.replace(' ','_')
            if len(titles) > 1:
                summary += '\n' + 'Similar: ' + ', '.join(titles[:4])
            message.reply(summary)

        

class HelpPLugin(SkypeBotPlugin):
    activator_commands = ['help']
    
    def on_command(self, message, command, input):
        text = 'Available commands:\n'
        call_name = self.bot.call_name + ' ' if not message.is_direct else ''
        for plugin in self.bot.enabled_plugins:
            if plugin.activator_commands:
                text += '%s %s\n' % (call_name, plugin.activator_commands[0])

        message.reply(text)

class AsciiPLugin(SkypeBotPlugin):
    activator_commands = ['ascii']
    
    def on_command(self, message, command, input):
        try:
            url = 'http://asciime.heroku.com/generate_ascii'
            ascii = requests.get(url, params=dict(s=input)).content
            
            message.reply(ascii)
        except Exception, e:
            print e



class GoogleMapsPlugin(SkypeBotPlugin):
    activator_commands = ['map', 'maps']
    
    def on_command(self, message, command, input):
        message.reply('http://maps.google.com/maps?q=' + requests.utils.urllib.quote(input.strip()))


import json
import re

class MathPlugin(SkypeBotPlugin):
    activator_commands = ['expr']
    
    def on_command(self, message, command, input):
        headers = {
            'Accept': 'application/xml',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Charset': 'utf-8',
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"
        }
        try:
            data = requests.get('http://www.google.com/ig/calculator', headers=headers, params={'h1': 'en', 'q': input})
            result = re.search(r'rhs: \"(.*?)\"', data.content).group(1)
            html = BeautifulSoup(unicode(result), convertEntities=BeautifulSoup.HTML_ENTITIES)
            for el in html.recursiveChildGenerator():
                if not isinstance(el, unicode) and el.name == 'sup':
                    el.replaceWith('^' + el.text)
            print html
            message.reply(html)
        except Exception, e:
            print e
            message.reply('Could not compute.')
        




def usage():
    print "python bot.py [options]"
    print " -h --help    : print this help"
    print " -v --verbose : verbose output"
    sys.exit()

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:v",
                                ["help", "watchlist"])

    except getopt.GetoptError:
        usage()
   
    use_verbose = False
    for opt, value in opts:
        if opt in ("-h", "--help"):
            usage()
        if opt in ("-v", "--verbose"):
            use_verbose = True

    #if not args:
    #    usage()

    bot = SkypeBot()
    bot.start()
    

if __name__ == "__main__":
    main()
    

