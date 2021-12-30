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
import os
import glob
import time
from mycroft import intent_handler, AdaptIntent
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from threading import Thread, Event
from pytube import YouTube

class FileLoaderThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.url = ''
        self.mp3_filename = ''
        self.request = False
        self.finished = False

    def run(self):
        while True:
            if self.request:
                self.request = False
                self.finished = False
                os.system("rm %s" % (self.mp3_filename,))  # clean up

                # grab the mp4
                mp4_filename = "/tmp/ytvid.mp4"
                video_url = "https://www.youtube.com/watch?v=%s" % (self.url,)
                yt = YouTube(video_url)
                yt.streams.first().download()
                os.rename(yt.streams.first().default_filename, mp4_filename)

                # convert to mp3
                cmd = "ffmpeg -i %s -q:a 0 -map a %s" % (mp4_filename, self.mp3_filename)
                os.system(cmd)
                os.system("rm %s" % (mp4_filename,))  # clean up

                self.finished = True
            time.sleep(1)

class DemoMusicSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="DemoMusicSkill")
        self.log.error('YTMUSIC INIT1')

    def initialize(self):
        self.log.error('YTMUSIC INIT2')
        self.mp3_filename = "/tmp/ytvid.mp3"
        self.th = FileLoaderThread()
        self.th.start()
        self.log.error('YTMUSIC INIT3')

    def get_url(self):
        try:
            fh = open("/tmp/search_results.html")
        except:
            self.log.error("Creepy internal error 101")
            return None

        for line in fh:
            if line.find("videoId") > 0:
                start_pos = line.find("videoId") + 10
                end_pos = line.find('"', start_pos)
                fh.close()
                return( line[start_pos:end_pos] )

    def CPS_match_query_phrase(self, msg: str) -> tuple((str, float, dict)):
        """Respond to Common Play Service query requests.
        Args:
            phrase: utterance request to parse
        Returns:
            Tuple(Name of station, confidence, Station information)
        """
        whack_these = ["'", "i", "me", "want", "like", "to", "hear", "play", "listen", "lsten", "some", "so"]
        for word in whack_these:
            msg = msg.replace(word, "")

        msg = msg.replace("&", "and")
        msg = msg.replace("  ", " ")
        msg = msg.strip()      # speakable topic

        search_term = msg.replace(" ", "+")  # url encode it :-)
        cmd = "wget -O /tmp/search_results.html https://www.youtube.com/results?search_query=%s" % (search_term,)
        os.system(cmd)
        url = self.get_url()
        self.log.error("YTMusic: search term = %s, url=%s" % (search_term,url))

        if url is None:
            # no results found
            self.log.error("No results found. Consult /tmp/search_results.html for more information")
            return ('not_found', CPSMatchLevel.CATEGORY, {})

        self.th.url = url
        self.th.mp3_filename = self.mp3_filename
        self.th.request = True

        self.log.error("Results found")
        match_level = CPSMatchLevel.EXACT
        return ('found', match_level, {'original_utterance':msg})

    def CPS_start(self, _, data):
        """Handle request from Common Play System to start playback."""
        self.log.error('CPS START MUSIC')

        ctr = 0
        while not self.th.finished:
            self.log.error("Waiting for download to complete")
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

        self.log.error('Download competed')
        mime = 'audio/mpeg'
        self.CPS_play((self.mp3_filename, mime))

    def stop(self) -> bool:
        """Respond to system stop commands."""
        self.CPS_send_status()
        return True

def create_skill():
    return DemoMusicSkill()


