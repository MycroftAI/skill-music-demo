# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os, time
import urllib.parse
from mycroft import intent_handler, AdaptIntent
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from .ytutils import FileLoaderThread, get_url

class DemoMusicSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="DemoMusicSkill")

    def initialize(self):
        self.mp3_filename = "/tmp/ytvid.mp3"
        self.artist = ''
        self.song = ''
        self.song_len = 0

        self.th = FileLoaderThread()
        self.th.start()

        self.actively_playing = False
        self.debounce = time.time()

        # get from config
        self.platform = "mycroft_mark_2" 
        self.register_gui_handlers()

        os.system("rm /tmp/ytvid.mp3")
        os.system("rm /tmp/ytvid.mp4")
        self.start_download_time = time.time()


    def register_gui_handlers(self):
        """Register handlers for events to or from the GUI."""
        self.bus.on('mycroft.audio.service.pause', self.handle_media_pause)
        self.bus.on('mycroft.audio.service.resume', self.handle_media_resume)
        self.bus.on('mycroft.audio.queue_end', self.handle_media_finished)
        self.gui.register_handler('cps.gui.restart', self.handle_gui_restart)
        self.gui.register_handler('cps.gui.pause', self.handle_gui_pause)
        self.gui.register_handler('cps.gui.play', self.handle_gui_play)

    def handle_gui_restart(self,msg):
        if time.time() - self.debounce < 3:
            return 

        self.debounce = time.time()
        self.bus.emit(Message('mycroft.audio.service.stop'))
        time.sleep(1.5)
        mime = 'audio/mpeg'
        self.CPS_play((self.mp3_filename, mime))

    def handle_gui_pause(self,msg):
        self.gui['status'] = "Paused"
        self.bus.emit(Message('mycroft.audio.service.pause'))

    def handle_gui_play(self,msg):
        self.gui['status'] = "Playing"
        self.bus.emit(Message('mycroft.audio.service.resume'))

    def handle_media_pause(self,msg):
        self.gui['status'] = "Paused"

    def handle_media_resume(self,msg):
        self.gui['status'] = "Playing"

    def handle_media_finished(self, message):
        """Handle media playback finishing."""
        self.actively_playing = False
        try:
            self.gui.release()
        except:
            pass

    def get_match_level(self, search_term, title, artist):
        return CPSMatchLevel(1 + (len( set(search_term.split(' ')) - ( set.union( set(title.split(' ')) , set(artist.split(' ')) ) ) ) ))

    def CPS_match_query_phrase(self, msg: str) -> tuple((str, float, dict)):
        """Respond to Common Play Service query requests.
        """
        msg = msg.replace(' by ',' ')
        if msg.startswith('play '):
            msg = msg[len('play '):]

        if msg.startswith('listen '):
            msg = msg[len('listen '):]

        msg = msg.strip()
        msg = msg.replace('&', ' and ')
        msg = msg.replace('  ', ' ')
        msg = msg.strip()  

        search_term = urllib.parse.quote_plus(msg)
        cmd = "wget -O /tmp/search_results.html https://www.youtube.com/results?search_query=%s" % (search_term,)
        os.system(cmd)
        url, img_url, artist, song, song_len = get_url()

        if url is None or song_len == 0:
            # no results found or len 0 usually means a stream
            self.log.debug("DemoMusicSkill: No results found. Consult /tmp/search_results.html for more information")
            return ('not_found', CPSMatchLevel.GENERIC, {})  

        self.start_download_time = time.time()
        self.th.url = url
        self.th.img_url = img_url
        self.th.mp3_filename = self.mp3_filename
        self.th.request = True  # initiates a download request
        self.artist = artist
        self.song = song
        self.song_len = song_len
        match_level = self.get_match_level(search_term, song, artist)
        match_term = artist + ' ' + song
        return ( match_term, match_level, {'original_utterance':search_term, 'resource_url':url} )

    def _show_gui_page(self, page):
        """Show a page variation depending on platform."""
        if self.gui.connected:
            if self.platform == "mycroft_mark_2":
                qml_page = f"{page}_mark_ii.qml"
            else:
                qml_page = f"{page}_scalable.qml"
            self.gui.show_page(qml_page, override_idle=True)

    def CPS_start(self, _, data):
        """Handle request from Common Play System to start playback."""
        ctr = 0
        self.actively_playing = True
        while not self.th.finished:
            self.log.debug("Waiting for download to complete: %s - %s" % (self.th.finished, self.actively_playing))
            if not self.actively_playing:
                # cancelled
                return

            # some things can take a while
            time.sleep(1)
            ctr += 1
            if ctr == 40:
                self.speak("Downloading of play list almost completed.")
                ctr = 0
            if ctr == 30:
                self.speak("Sorry this is taking so long. Almost ready to play.")
            if ctr == 20:
                self.speak("Still downloading media, sorry for the delay.")
            if ctr == 10:
                self.speak("Downloading your selection, please wait.")

        img_filename = self.th.img_filename
        self.log.debug("Download competed, img_filename=%s" % (img_filename,))
        mime = 'audio/mpeg'
        self.CPS_play((self.mp3_filename, mime))

        if len(self.artist) > 15:
            self.artist = self.artist[:15]

        if len(self.song) > 25:
            self.song = self.song[:27] + '...'

        self.gui['media'] = {
            "image": img_filename,
            "artist": self.artist,
            "song": self.song,
            "length": self.song_len * 1000,
            "skill": self.skill_id,
            "streaming": 'true'
        }
        self.gui['theme'] = dict(fgColor="gray", bgColor="black")
        self.gui['status'] = "Playing"
        self._show_gui_page("AudioPlayer")
        self.CPS_send_status(
            image=img_filename,
            artist=self.artist
        )

    def stop(self) -> bool:
        """
        for some odd reason (perhaps playback handing off to us or
        due to recent refactoring of the skill base class) we get a 
        stop() call almost immediately, so we simply wait until at 
        least x seconds have passed before we honor any stop() calls
        """
        elapsed = time.time() - self.start_download_time
        if elapsed > 5.0:
            # only process if at least 5 seconds have 
            # passed since we started a download
            self.start_download_time = time.time()
            self.CPS_send_status()
            if self.actively_playing:
                self.actively_playing = False  # cancel download
                try:
                    self.gui.release()
                except:
                    pass
            return True
        else:
            return False

def create_skill():
    return DemoMusicSkill()
