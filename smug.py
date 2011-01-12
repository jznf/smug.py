#!/usr/bin/env python
#author Tejeshwar Sangam - tejeshwar.s@gmail.com
#https://github.com/colorfulgrayscale/smug

print "Searching for music files",
import os, sys, tty, termios, threading, time, optparse, random, platform
from subprocess import Popen, PIPE
from datetime import timedelta, datetime

if platform.system() != 'Darwin':
    print "This program works only on MacOS X"
    exit()

parser=optparse.OptionParser()
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

class MusicFile:
    def __init__(self, name=None, path=None):
        self.name = name
        self.path = path
    def __str__(self):
        return ("%s/%s" % (self.path, self.name))

class Playlist:
    def __init__(self):
        self.playlist = list()
        self.currentlyPlaying = -1
        self.supportedFiles = ['.mp3', '.wav', '.flac','.aif']
        self.random = False
        self.repeat = False
    def add(self, filename, folder):
        basename, extension = os.path.splitext(filename)
        if extension in self.supportedFiles:
            self.playlist.append(MusicFile(name=filename, path=folder))
    def addFolder(self, folder):
        for filename in os.listdir(folder):
            self.add(filename,folder)
    def addFolderRecursive(self,folder):
        for root, subFolders, files in os.walk(folder):
            for filename in files:
                self.add(filename, root)
    def count(self):
        return len(self.playlist)
    def currentSong(self):
        return self.playlist[self.currentlyPlaying]
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
        if self.random:
            return self.randomSong()
        if (self.currentlyPlaying+1) > (len(self.playlist)-1) :
            return self.firstSong()
        self.currentlyPlaying = self.currentlyPlaying + 1
        return self.playlist[self.currentlyPlaying]
    def prevSong(self):
        if self.repeat:
            return self.currentSong()
        if self.random:
            return self.randomSong()
        if (self.currentlyPlaying-1 < 0):
            return self.lastSong()
        self.currentlyPlaying = self.currentlyPlaying - 1
        return self.playlist[self.currentlyPlaying]
    def toggleRepeat(self):
        if self.repeat:
            print "X. [Stop Looping Track %s]"%self.currentSong().name
            self.repeat = False
        else:
            print "X. [Start Looping Track %s]"%self.currentSong().name
            self.repeat = True

playlist = Playlist()

class Player:
    def __init__(self):
        self.playHistory = list()
        self.isPlaying = False
        self.playerPID = -1
        self.player = -1
    def getDuration(self, musicFile):
        command = "afinfo \"%s\"|awk 'NR==5'|tr -d '\n'|awk '{print $3}'" % musicFile
        raw = Popen(command, shell=True, stdout=PIPE).stdout.readline().strip()
        sec = timedelta(seconds=int(float(raw)))
        duration = datetime(1,1,1) + sec
        return("%d:%d" % (duration.minute, duration.second))
    def play(self,musicFile):
        if ch == 'q':
            return
        print "\r%d. %s - [fetching time...]" % (len(self.playHistory)+1, musicFile.name),
        print "\r%d. %s - %s mins %5s" % (len(self.playHistory)+1, musicFile.name,self.getDuration(musicFile),''),
        if playlist.repeat:
            print "[Looping]%20s\r\n"%'',
        else:
            print "%20s\r\n"%'',
        self.stop()
        self.isPlaying = True
        self.playHistory.append(musicFile)
        self.player = Popen("afplay \"%s\" -q 1" % musicFile, shell=True)
        self.playerPID = self.player.pid
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
        print "\r  [Paused]%20s\r"%'',
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

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
class playerThread(threading.Thread):
    def run(self):
        global ch
        playlist.random = options.shuffle
        if options.recursive:
            playlist.addFolderRecursive(os.getcwd())
        else:
            playlist.addFolder(os.getcwd())
        print "Found %d music file(s).\n" % playlist.count()
        if (playlist.count()<=0):
            ch = 'q'
            exit()
        updaterThread().start()
        while (ch!='q') :
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            playerControls(ch)

class updaterThread(threading.Thread):
    def run(self):
        player.play(playlist.nextSong())
        global ch
        while (ch!='q'):
            try:
                time.sleep(1)
            except:
                pass
            if(player.trackFinished()):
                player.play(playlist.nextSong())

def playerControls(ch):
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
    elif (ch=='q'):
        print "\nQuiting..."
        player.stop()
        exit()
    elif (ch==' '):
        player.togglePlayPause()

if __name__ == '__main__':
    playerThread().start()
