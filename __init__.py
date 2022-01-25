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
import threading
import typing
from enum import Enum

from mycroft import intent_handler, AdaptIntent
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.messagebus import Message
from mycroft.util.log import LOG

from pytube import Search


class State(str, Enum):
    INACTIVE = "inactive"
    SEARCHING = "searching"
    PLAYING = "playing"
    PAUSED = "paused"


class DemoMusicSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="DemoMusicSkill")

    def initialize(self):
        self.state: State = State.INACTIVE
        self.state: State = State.INACTIVE

        # get from config
        self.platform = "mycroft_mark_2"
        self.register_gui_handlers()

        # Thread used to search YouTube
        self.search_thread: typing.Optional[threading.Thread] = None

        # Event to signal main thread when search is complete
        self.search_ready = threading.Event()

        # Selected search result from YouTube
        self.result = None

        # Selected audio stream to play from search result
        self.stream = None

        self._player_position_ms: int = 0

    def register_gui_handlers(self):
        """Register handlers for events to or from the GUI."""
        self.bus.on("mycroft.audio.service.pause", self.handle_media_pause)
        self.bus.on("mycroft.audio.service.resume", self.handle_media_resume)
        self.bus.on("mycroft.audio.service.position", self.handle_media_position)
        self.bus.on("mycroft.audio.queue_end", self.handle_media_finished)
        self.gui.register_handler("cps.gui.restart", self.handle_gui_restart)
        self.gui.register_handler("cps.gui.pause", self.handle_gui_pause)
        self.gui.register_handler("cps.gui.play", self.handle_gui_play)

    @intent_handler(AdaptIntent("").require("Show").require("Music"))
    def handle_show_music(self, message):
        with self.activity():
            self._setup_gui()
            self._show_gui_page("AudioPlayer")

    def handle_gui_restart(self, msg):
        pass

    def handle_gui_pause(self, msg):
        if self.state == State.PLAYING:
            self.state = State.PAUSED

        self.gui["status"] = "Paused"
        self.bus.emit(Message("mycroft.audio.service.pause"))

    def handle_gui_play(self, msg):
        if self.state == State.PAUSED:
            self.state = State.PLAYING

        self.gui["status"] = "Playing"
        self.bus.emit(Message("mycroft.audio.service.resume"))
        self.gui["position"] = self._player_position_ms

    def handle_media_pause(self, msg):
        if self.state == State.PLAYING:
            self.state = State.PAUSED

        self.gui["status"] = "Paused"

    def handle_media_resume(self, msg):
        if self.state == State.PAUSED:
            self.state = State.PLAYING

        self.gui["status"] = "Playing"

    def handle_media_position(self, msg):
        position_ms = msg.data.get("position_ms")
        if (position_ms is not None) and (position_ms >= 0):
            self._player_position_ms = position_ms

    def handle_media_finished(self, message):
        """Handle media playback finishing."""
        self._go_inactive()

    def CPS_match_query_phrase(self, phrase: str) -> tuple((str, float, dict)):
        """Respond to Common Play Service query requests.
        """
        phrase = phrase.strip()

        if not phrase:
            return None

        phrase = phrase.replace(" by ", " ")

        for word in ["play", "listen"]:
            if phrase.startswith(word):
                phrase = phrase[len(word) :]
                break

        phrase = phrase.strip()
        phrase = phrase.replace("&", " and ")
        phrase = phrase.replace("  ", " ")
        phrase = phrase.strip()

        # Run search in separate thread
        self._search_for_music(phrase)

        # Assume we'll get something
        return (phrase, CPSMatchLevel.EXACT, {})

    def _search_for_music(self, phrase: str):
        """Run search in separate thread to avoid CPS timeouts"""
        self.search_ready.clear()
        self.state = State.SEARCHING

        self.result = None
        self.stream = None
        self.search_thread = threading.Thread(
            target=self._run_search, daemon=True, args=(phrase,)
        )
        self.search_thread.start()

    def _run_search(self, phrase: str):
        """Search YouTube and grab first audio stream"""
        try:
            LOG.info("Searching YouTube for %s", phrase)
            yt_results = Search(phrase).results

            for result in yt_results:
                try:
                    # From the docs:
                    #
                    # Raises different exceptions based on why the video
                    # is unavailable, otherwise does nothing.
                    result.check_availability()
                except Exception:
                    # Skip result
                    continue

                for stream in result.streams:
                    if stream.includes_audio_track:
                        # Take the first available stream with audio
                        self.result = result
                        self.stream = stream
                        break

                if self.stream is not None:
                    break

            if (self.stream is None) or (self.result is None):
                LOG.error("No stream found")
            else:
                LOG.info("Stream found")
        except Exception:
            LOG.exception("error searching YouTube")
        finally:
            self.search_ready.set()

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
        search_successful = self.search_ready.wait(timeout=20)

        if (not search_successful) or (self.stream is None) or (self.result is None):
            self.speak("No search results were found.")

            # We've already been stopped by CPS, so not much else to do
            self._go_inactive()
            return

        # Reset existing media
        self.gui["status"] = "Stopped"

        # This is critical for some reason
        mime = "audio/mpeg"

        self.CPS_play((self.stream.url, mime))

        self._player_position_ms = 0
        self._setup_gui()
        self.gui["status"] = "Playing"

        self._show_gui_page("AudioPlayer")

        self.state = State.PLAYING

    def _setup_gui(self):
        self.gui["theme"] = dict(fgColor="gray", bgColor="black")

        if (self.result is None) or (self.stream is None):
            return

        artist = self.result.author
        song = self.result.title

        if len(artist) > 15:
            artist = artist[:15]

        if len(song) > 25:
            song = song[:27] + "..."

        media_settings = {
            "image": self.result.thumbnail_url,
            "artist": artist,
            "song": song,
            "length": self.result.length * 1000,
            "skill": self.skill_id,
            "streaming": "true",
            "position": self._player_position_ms,
        }

        self.gui["media"] = media_settings
        self.gui["position"] = self._player_position_ms

    def stop(self) -> bool:
        LOG.info("Stopping")

        self._go_inactive()

        return True

    def _go_inactive(self):
        if self.state == State.PLAYING:
            self.state = State.PAUSED
        else:
            self.state = State.INACTIVE

        self.gui["status"] = "Paused"
        if self.gui.connected:
            self.gui.release()

        LOG.info("Music is now inactive")


def create_skill():
    return DemoMusicSkill()
