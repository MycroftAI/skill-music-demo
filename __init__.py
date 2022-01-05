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
import os, re, glob, time, json
import urllib.parse
from mycroft import intent_handler, AdaptIntent
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from threading import Thread, Event
from pytube import YouTube
from mycroft.messagebus import Message


class FileLoaderThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.url = ''
        self.img_url = ''
        self.img_filename = ''
        self.mp3_filename = ''
        self.img_ctr = 0
        self.request = False
        self.finished = False

    def run(self):
        while True:
            if self.request:
                self.request = False
                self.finished = False

                # clean up after yourself
                if self.mp3_filename != '':
                    os.system("rm -f %s" % (self.mp3_filename,))  
                if self.img_filename != '':
                    os.system("rm -f %s" % (self.img_filename,)) 

                # grab image
                self.img_ctr += 1
                img_filename = "/tmp/music_img%s" % (self.img_ctr,)
                if self.img_url.endswith(".jpg"):
                    img_filename += ".jpg"
                elif self.img_url.endswith(".gif"):
                    img_filename += ".gif"
                else:
                    img_filename += ".png"

                self.img_filename = img_filename

                cmd = "wget -O %s %s" % (img_filename, self.img_url)
                os.system(cmd)

                # grab the mp4
                mp4_filename = "/tmp/ytvid.mp4"
                video_url = "https://www.youtube.com/watch?v=%s" % (self.url,)
                yt = YouTube(video_url)
                yt.streams.first().download()
                os.rename(yt.streams.first().default_filename, mp4_filename)

                # convert to mp3
                cmd = "ffmpeg -i %s -q:a 0 -map a %s" % (mp4_filename, self.mp3_filename)
                os.system(cmd)
                os.system("rm -f %s" % (mp4_filename,))  # clean up

                self.finished = True
            time.sleep(1)


class DemoMusicSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="DemoMusicSkill")

    def initialize(self):
        self.mp3_filename = "/tmp/ytvid.mp3"
        self.artist = ''
        self.song = ''
        self.th = FileLoaderThread()
        self.th.start()
        self.debounce = time.time()

        # get from config
        self.platform = "mycroft_mark_2" 
        self.register_gui_handlers()


    def register_gui_handlers(self):
        """Register handlers for events to or from the GUI."""
        self.bus.on('mycroft.audio.service.pause', self.handle_media_pause)
        self.bus.on('mycroft.audio.service.resume', self.handle_media_resume)
        self.bus.on('mycroft.audio.queue_end', self.handle_media_finished)
        self.bus.on('demo-music.cps.gui.restart', self.handle_gui_restart)
        self.bus.on('demo-music.cps.gui.pause', self.handle_gui_pause)
        self.bus.on('demo-music.cps.gui.play', self.handle_gui_play)

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

    def handle_media_finished(self,msg):
        pass

    def get_json(self):
        fh = open("/tmp/search_results.html")
        tag = 'var ytInitialData ='
        for line in fh:

            if line.find(tag) != -1:
                la = line.split("</script>")
                ctr = 0
                for l in la:
                    ctr += 1
                    if l.find(tag) != -1:
                        start_indx = l.find(tag) + len(tag) + 1
                        fh.close()
                        return l[start_indx:-1]
        fh.close()
        return ''

    def get_url(self):
        vid_json = json.loads( self.get_json() )
        contents = vid_json['contents']
        rend = contents['twoColumnSearchResultsRenderer']
        rend = rend['primaryContents']
        rend = rend['sectionListRenderer']
        rend = rend['contents']
        rend = rend[0]
        rend = rend['itemSectionRenderer']
        rend = rend['contents']
        rend = rend[0]
        rend = rend['videoRenderer']

        # at this point rend is the first video renderer
        video_id = rend['videoId']
        thumb = rend['thumbnail']['thumbnails'][0]
        img_url = thumb['url']
        ia = img_url.split("?")
        img_url = ia[0]
        title = rend['title']['runs'][0]['text']

        # sometimes we have artist and song
        ta = title.split(" - ")
        artist = ta[0]
        song = artist
        if len(ta) > 1:
            song = ta[1]

        if song == artist:
            ta = title.split(" by ")
            artist = ta[0]
            song = artist
            if len(ta) > 1:
                song = ta[1]

        # remove everything in parens
        # might be a bit harsh
        artist = re.sub(r'\([^)]*\)', '', artist)
        song = re.sub(r'\([^)]*\)', '', song)

        return video_id, img_url, artist, song

    def CPS_match_query_phrase(self, msg: str) -> tuple((str, float, dict)):
        """Respond to Common Play Service query requests.
        Args:
            phrase: utterance request to parse
        Returns:
            Tuple(Name of station, confidence, Station information)
        """
        whack_these = ["'", "i", "me", "want", "like", "to", "hear", "play", "listen", "lsten", "some", "so"]

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
        url, img_url, artist, song = self.get_url()
        self.log.debug("YTMusic: Search term = %s, url=%s, image=%s, artist=%s, song=%s" % (search_term,url,img_url, artist, song))

        if url is None:
            # no results found
            self.log.error("YTMusic: No results found. Consult /tmp/search_results.html for more information")
            return ('not_found', CPSMatchLevel.CATEGORY, {})

        self.th.url = url
        self.th.img_url = img_url
        self.th.mp3_filename = self.mp3_filename
        self.th.request = True
        self.artist = artist
        self.song = song

        match_level = CPSMatchLevel.EXACT
        return ('found', match_level, {'original_utterance':search_term})

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
        while not self.th.finished:
            self.log.debug("Waiting for download to complete")
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

        if len(self.artist) > 19:
            self.artist = self.artist[:19]

        if len(self.song) > 25:
            self.song = self.song[:25]

        self.gui['media'] = {
            "image": img_filename,
            "artist": self.artist,
            "song": self.song,
            "album": 'MIA album',
            "skill": self.skill_id,
            "streaming": True
        }
        self.gui['status'] = "Playing"
        self.gui['theme'] = dict(fgColor="gray", bgColor="black")
        self._show_gui_page("AudioPlayer")
        self.CPS_send_status(
            image=img_filename,
            artist=self.artist
        )

    def stop(self) -> bool:
        self.CPS_send_status()
        return True

def create_skill():
    return DemoMusicSkill()

