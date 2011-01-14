#!/usr/bin/env python
#author Tejeshwar Sangam - tejeshwar.s@gmail.com
#https://github.com/colorfulgrayscale/smug

import os, sys, tty, termios, threading, time, optparse, random, platform, difflib
from subprocess import Popen, PIPE
from datetime import timedelta, datetime

if platform.system() != 'Darwin':
    print "This program works only on MacOS X"
    exit()

parser=optparse.OptionParser(usage='%prog [file/folder] --shuffle --recursive', version='0.1',)
parser.add_option(
  '-s','--shuffle',
  dest='shuffle',
  default=False,
  action="store_true",
  help='''Shuffle mode.'''
)
parser.add_option(
  '-r','--recursive',
  dest='recursive',
  default=False,
  action="store_true",
  help='''Find music files recursively'''
)
options,args=parser.parse_args()
ch = '~'
autoPlayNextTrack=True

class MusicFile:
    def __init__(self, name=None, path=None):
        self.name = name
        self.path = path
    def __str__(self):
        return ("%s/%s" % (self.path, self.name))

class Playlist:
    def __init__(self):
        self.playlist = list()
        self.randomHistory = list()
        self.currentlyPlaying = -1
        self.supportedFiles = ['.mp3', '.wav','.aif','.m4a']
        self.repeat = False
    def add(self, filename, folder):
        basename, extension = os.path.splitext(filename)
        if extension in self.supportedFiles:
            self.playlist.append(MusicFile(name=filename, path=folder))
    def addFolder(self, folder):
        if options.recursive:
            for root, subFolders, files in os.walk(folder):
                for filename in files:
                    self.add(filename, root)
        else:
            for filename in os.listdir(folder):
                self.add(filename,folder)
    def addGeneric(self, name):
        if os.path.isdir(name):
            self.addFolder(name)
        elif os.path.isfile(name):
            folder, filename = os.path.split(name)
            if not folder:
                folder = os.getcwd()
            self.add(filename, folder)
        else:
            return -1
    def count(self):
        return len(self.playlist)
    def currentSong(self):
        return self.playlist[self.currentlyPlaying]
    def findSong(self, song):
        if song.isdigit() and int(song)<=len(self.playlist):
            self.currentlyPlaying = int(song) - 1
            return self.playlist[self.currentlyPlaying]
        searchIndex = -1
        highestMatchRatio = -1
        thresholdRatio = 0.2
        for (counter, files) in enumerate(self.playlist):
            temp = difflib.SequenceMatcher(None, files.name, song).ratio()
            if (temp > highestMatchRatio) and (temp > thresholdRatio):
                searchIndex = counter
                highestMatchRatio = temp
        if(searchIndex!=-1):
            self.currentlyPlaying = searchIndex
            return self.playlist[self.currentlyPlaying]
        return -1
    def randomSong(self):
        self.currentlyPlaying = random.randrange(len(self.playlist))
        return self.playlist[self.currentlyPlaying]
    def firstSong(self):
        if(len(self.playlist)>0):
            self.currentlyPlaying = 0
            return self.playlist[0]
    def lastSong(self):
        if(len(self.playlist)>0):
            self.currentlyPlaying = len(self.playlist) - 1
            return self.playlist[-1]
    def nextSong(self):
        if self.repeat:
            return self.currentSong()
        if options.shuffle:
            song = self.randomSong()
            playlist.randomHistory.append(song)
            return song
        if (self.currentlyPlaying+1) > (len(self.playlist)-1) :
            return self.firstSong()
        self.currentlyPlaying = self.currentlyPlaying + 1
        return self.playlist[self.currentlyPlaying]
    def prevSong(self):
        if self.repeat:
            return self.currentSong()
        if options.shuffle:
            if len(self.randomHistory) <=1:
                return self.randomHistory[0]
            else:
                song = self.randomHistory.pop()
                if "%s"%song == "%s"%self.currentSong():
                    return self.randomHistory.pop()
                else:
                    return song
        if (self.currentlyPlaying-1 < 0):
            return self.lastSong()
        self.currentlyPlaying = self.currentlyPlaying - 1
        return self.playlist[self.currentlyPlaying]
    def toggleRepeat(self):
        if self.repeat:
            print "X. [Single Track Looping Disabled]"
            self.repeat = False
        else:
            print "X. [Single Track Looping Enabled]"
            self.repeat = True
    def __str__(self):
        print "\nPlaylist had %d file(s)"%len(self.playlist)
        print '-'*50
        for (counter, files) in enumerate(self.playlist):
            if counter == self.currentlyPlaying:
                print "-> ",
            print "%d. %s "%(counter+1, files.name)
        print '-'*50
        return ""

playlist = Playlist()

class Player:
    def __init__(self):
        self.isPlaying = False
        self.playerPID = -1
        self.player = -1
        self.playCounter = 0
        self.currentSong = str()
    def getDuration(self, musicFile):
        command = "afinfo \"%s\"|awk 'NR==5'|tr -d '\n'|awk '{print $3}'" % musicFile
        raw = Popen(command, shell=True, stdout=PIPE).stdout.readline().strip()
        sec = timedelta(seconds=int(float(raw)))
        duration = datetime(1,1,1) + sec
        return("%d:%d" % (duration.minute, duration.second))
    def play(self,musicFile):
        if ch == 'q':
            return
        self.playCounter = self.playCounter + 1
        print "\r%d. %s - [fetching time...]" % (self.playCounter, musicFile.name),
        self.stop()
        self.isPlaying = True
        self.player = Popen("afplay \"%s\" -q 1" % musicFile, shell=True)
        self.playerPID = self.player.pid
        self.currentSong = "\r%d. %s - %s mins" % (self.playCounter,  musicFile.name,self.getDuration(musicFile))
        if playlist.repeat:
            self.currentSong = "%s %s"%(self.currentSong, "[Looping]%20s\r"%'')
        else:
            self.currentSong = "%s %s"%(self.currentSong, "%20s\r"%'')
        print self.currentSong
    def stop(self):
        if(self.playerPID== -1) or (self.isPlaying==False):
            return
        self.isPlaying = False
        try:
            self.player.kill()
        except:
            pass
    def pause(self):
        if(self.playerPID==-1) or (self.isPlaying==False):
            return
        print "\r  [Muted]%20s\r"%'',
        Popen("kill -STOP %d " % self.playerPID, shell=True)
        self.isPlaying = False
    def resume(self):
        if(self.playerPID==-1) or (self.isPlaying==True):
            return
        print "\r%20s\r"%'',
        Popen("kill -CONT %d" % self.playerPID, shell=True)
        self.isPlaying = True
    def togglePlayPause(self):
        if(self.isPlaying):
            self.pause()
        else:
            self.resume()
    def trackFinished(self):
        try:
            a = self.player.poll()
        except:
            return False
        if(a==0):
            return True
        else:
            return False

player = Player()

class playerThread(threading.Thread):
    def run(self):
        global ch
        if(len(args)>0):
            sucess = playlist.addGeneric(args[0])
            if sucess == -1:
                print "%s not found!"%args[0]
                exit()
        else:
            playlist.addFolder(os.getcwd())
        print "Found %d music file(s).\n" % playlist.count()
        if (playlist.count()<=0):
            ch = 'q'
            exit()
        updaterThread().start()
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        while (ch!='q') :
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            playerControls()

class updaterThread(threading.Thread):
    def run(self):
        player.play(playlist.nextSong())
        global ch, autoPlayNextTrack
        while (ch!='q'):
            try:
                time.sleep(1)
            except:
                pass
            if(player.trackFinished() and autoPlayNextTrack):
                player.play(playlist.nextSong())

def playerControls():
    global ch, autoPlayNextTrack
    if (ch=='n') or (ch=='j'):
        player.play(playlist.nextSong())
    elif (ch=='p') or (ch=='k'):
        player.play(playlist.prevSong())
    elif (ch=='r'):
        player.play(playlist.currentSong())
    elif (ch=='s'):
        player.play(playlist.randomSong())
    elif (ch=='l'):
        playlist.toggleRepeat()
    elif (ch=='i'):
        print "%s\n%s"%(playlist,player.currentSong)
    elif (ch=='/'):
        autoPlayNextTrack=False
        print "\r%30s\r"%'',
        foo = raw_input("X. Jump to song: ")
        song = playlist.findSong(foo)
        if(song == -1):
            print "\r  [Song Not Found!]%20s\r"%'',
        else:
            player.play(song)
        autoPlayNextTrack=True
    elif (ch=='q'):
        print "\nQuiting..."
        player.stop()
        exit()
    elif (ch==' '):
        player.togglePlayPause()

if __name__ == '__main__':
    print "Searching for music files"
    playerThread().start()
