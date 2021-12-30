


"""
Currently uncommented code will open a youtube video in a 
qml screen/page. User is required to actually press start.

Commented out code shows how to not play videos, but 
rather just the audio by downloading the video, pulling
out the mp3 and playing it using mpg123
"""

from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
import os
import glob
import subprocess

class KensMusic(MycroftSkill):
    def __init__(self):
        super().__init__()
        #self.learning = True

    def initialize(self):
        #my_setting = self.settings.get('my_setting')
        self.log.error("KensMusic:initialize()")


    def get_url(self):
        try:
            fh = open("/tmp/search_results.html")
        except:
            return None

        for line in fh:
            if line.find("videoId") > 0:
                start_pos = line.find("videoId") + 10
                end_pos = line.find('"', start_pos)
                fh.close()
                return( line[start_pos:end_pos] )


    @intent_handler(IntentBuilder('KensMusicIntent')
                    .require('KensMusicKeyword'))
    def handle_kens_music_intent(self, message):
        url = "https://www.youtube.com/watch?v=BD9r4n5Gsaw&start_radio=1"
        self.gui.show_url(url, override_idle=True, override_animations=True)
        """
        msg = message.data.get("utterance")
        # should probably just regex it 
        whack_these = ["'", "i", "me", "want", "like", "to", "hear", "play", "listen", "lsten", "some", "so"]
        for word in whack_these:
            msg = msg.replace(word, "")

        msg = msg.replace("&", "and")
        msg = msg.replace("  ", " ")
        msg = msg.strip()      # speakable topic

        search_term = msg.replace(" ", "+")  # url encode it :-)
        self.log.error("KensMusic: search term = %s" % (search_term,))

        # look for file in cache
        filename = "%s_sample.mp3" % (search_term,)
        fnames = glob.glob("/home/mycroft/Music/%s" % (filename,))

        if len(fnames) == 0:
            # not in cache
            self.speak(" by " + msg)

            cmd = "wget -O /tmp/search_results.html https://www.youtube.com/results?search_query=%s" % (search_term,)
            os.system(cmd)
            url = self.get_url()

            if url is None:
                self.speak("Music by %s not found" % (msg,))
                return None

            self.speak("OK, this may take a few seconds")

            cmd = "pytube https://www.youtube.com/watch?v=%s" % (url,)
            os.system(cmd)

            self.speak("Got it, let me convert it. This will only take a second or so. Bear with me, I'm getting faster every day")

            # find the downloaded file
            fnames = glob.glob("/opt/mycroft/*.mp4")
            fname = fnames[0]

            # rename it
            cmd = 'mv "%s" /opt/mycroft/input.mp4' % (fname,)
            os.system(cmd)

            # convert to mp3
            cmd = "ffmpeg -i /opt/mycroft/input.mp4 -q:a 0 -map a /home/mycroft/Music/%s" % (filename,)
            os.system(cmd)
            os.system("rm /opt/mycroft/input.mp4")  # clean up

        os.system("mpg123 /home/mycroft/Music/%s" % (filename,))
        """


    def stop(self):
        self.gui.remove_page("SYSTEM_UrlFrame.qml")
        """
        process = subprocess.Popen(
              ["ps", "-eo", "pid,cmd"],
              stdout=subprocess.PIPE,
              stderr=subprocess.PIPE,
        )
        out, err = process.communicate()
        out = out.decode("utf-8")
        err = err.decode("utf-8")

        plist = out.split("\n")
        line_ctr = len(plist)
        indx = 0
        while indx < line_ctr:
            cols = plist[indx].strip().split(" ")
            if len(cols) > 1 and cols[1].startswith("mpg123"):
                self.log.error("KensMusic found process to kill = [%s]%s" % (cols[0], plist[indx],))
                cmd = "kill %s" % (cols[0])
                os.system(cmd)

            indx += 1

        os.system("rm /opt/mycroft/input.mp4")
        """


def create_skill():
    return KensMusic()
