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

        os.system("rm /tmp/ytvid.mp3")
        os.system("rm /tmp/ytvid.mp4")

        self.bus.on('demo-music.cps.gui.restart', self.handle_gui_restart)

    def handle_gui_restart(self,msg):
        if time.time() - self.debounce < 3:
            return 

        self.debounce = time.time()
        self.bus.emit(Message('mycroft.audio.service.stop'))
        time.sleep(1.5)
        mime = 'audio/mpeg'
        self.CPS_play((self.mp3_filename, mime))

    def CPS_match_query_phrase(self, msg: str) -> tuple((str, float, dict)):
        """Respond to Common Play Service query requests.
        """
        #whack_these = ["'", "i", "me", "want", "like", "to", "hear", "play", "listen", "lsten", "some", "so"]
        whack_these = ["'", "hear", "play", "listen"]

        ma = msg.split(" ")
        msg = ''
        for m in ma:
            if m not in whack_these:
                msg += m + " "

        msg = msg.strip()
        msg = msg.replace("&", " and ")
        msg = msg.replace("  ", " ")
        msg = msg.strip()  
        search_term = urllib.parse.quote_plus(msg)
        cmd = "wget -O /tmp/search_results.html https://www.youtube.com/results?search_query=%s" % (search_term,)
        os.system(cmd)
        url, img_url, artist, song, song_len = get_url()
        self.log.debug("DemoMusicSkill: Search term = %s, url=%s, image=%s, artist=%s, song=%s, len=%sn" % (search_term,url,img_url, artist, song, song_len))

        if url is None or song_len == 0:
            # no results found or len 0 usually means a stream
            self.log.error("DemoMusicSkill: No results found. Consult /tmp/search_results.html for more information")
            return ('not_found', CPSMatchLevel.CATEGORY, {})

        self.th.url = url
        self.th.img_url = img_url
        self.th.mp3_filename = self.mp3_filename
        self.th.request = True
        self.artist = artist
        self.song = song
        self.song_len = song_len

        match_level = CPSMatchLevel.EXACT
        return ('found', match_level, {'original_utterance':search_term})

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
                self.speak("Still downloading, sorry for the delay.")
            if ctr == 10:
                self.speak("Downloading your music, please wait.")

        img_filename = self.th.img_filename
        self.log.debug("Download competed, img_filename=%s" % (img_filename,))
        mime = 'audio/mpeg'
        self.CPS_play((self.mp3_filename, mime))

        if len(self.artist) > 15:
            self.artist = self.artist[:15]

        if not self.artist:
            self.artist = " "

        if len(self.song) > 30:
            self.song = self.song[:27] + '...'

        self.CPS_send_status(image=img_filename, track=self.song)

        self.actively_playing = True
        self.CPS_send_status(
            image=img_filename,
            track=self.song,
            artist=self.artist
        )

def create_skill():
    return DemoMusicSkill()
