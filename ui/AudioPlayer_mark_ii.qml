/*
* Copyright 2021 by Aditya Mehra <aix.m@outlook.com>
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*/

import QtQuick 2.12
import QtMultimedia 5.12
import QtQuick.Controls 2.12 as Controls
import QtQuick.Templates 2.12 as T
import QtQuick.Layouts 1.3
import org.kde.kirigami 2.8 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    fillWidth: true
    skillBackgroundColorOverlay: "black"
    property var theme: sessionData.theme
    //cardBackgroundOverlayColor: Qt.darker(theme.bgColor)
    cardBackgroundOverlayColor: theme.bgColor
    cardRadius: Mycroft.Units.gridUnit

    // Track_Lengths, Durations, Positions are always in milliseconds
    // Position is always in milleseconds and relative to track_length if track_length = 530000, position values range from 0 to 530000

    property var media: sessionData.media
    property var playerDuration: media.length
    property var playerState: sessionData.status
    property real playerPosition: sessionData.position
    property bool isStreaming: media.streaming
    property bool streamTimerPaused: false

    function formatTime(ms) {
        if (typeof(ms) !== "number") {
            return "";
        }
        var minutes = Math.floor(ms / 60000);
        var seconds = ((ms % 60000) / 1000).toFixed(0);
        return minutes + ":" + (seconds < 10 ? '0' : '') + seconds;
    }

    onPlayerStateChanged: {
        //console.log(playerState)
        if (!isStreaming) {
            root.playerPosition = media.position
        }
        if(playerState === "Playing"){
            streamTimer.running = true
        } else if(playerState === "Paused") {
            streamTimer.running = false
        } else if(playerState === "Stopped") {
            streamTimer.running = false
            root.playerPosition = 0
        }
    }

    Timer {
        id: streamTimer
        interval: 1000
        running: false
        repeat: true
        onTriggered: {
            if(!streamTimerPaused){
                playerPosition = playerPosition + 1000
            }
        }
    }

    Rectangle {
        id: cardContents
        anchors.fill: parent
        radius: Mycroft.Units.gridUnit
        color: Qt.darker(theme.bgColor)

        Rectangle {
            id: imageContainer
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: trackInfo.top
            anchors.topMargin: Mycroft.Units.gridUnit * 1
            color: "transparent"

            Image {
                id: trackImage
                visible: true
                enabled: true
                height: Mycroft.Units.gridUnit * 16
                width: Mycroft.Units.gridUnit * 28
                anchors.horizontalCenter: parent.horizontalCenter
                source: media.image
                fillMode: Image.PreserveAspectCrop
                z: 100
            }
        }

        Rectangle {
            id: trackInfo
            anchors.bottom: sliderContainer.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            height: Mycroft.Units.gridUnit * 6
            color: "transparent"

            Rectangle {
                id: titleContainer
                width: Mycroft.Units.gridUnit * 28
                anchors.horizontalCenter: parent.horizontalCenter
                color: "transparent"

                Title {
                    id: trackTitle
                    anchors.top: parent.top
                    font.pixelSize: 24
                    color: theme.fgColor
                    heightUnits: 2
                    text: media.song
                    maxTextLength: 40
                }

                Title {
                    id: artistName
                    anchors.top: trackTitle.bottom
                    font.pixelSize: 47
                    font.styleName: "Bold"
                    color: theme.fgColor
                    heightUnits: 3
                    text: media.artist
                    maxTextLength: 17
                }
            }

            
            
            RowLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Mycroft.Units.gridUnit / 2
                visible: media.length !== -1 ? 1 : 0
                enabled: media.length !== -1 ? 1 : 0
                
                Controls.Label {
                    Layout.alignment: Qt.AlignLeft
                    Layout.leftMargin: Mycroft.Units.gridUnit * 2
                    font.pixelSize: 35
                    font.bold: true
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    text: formatTime(playerPosition)
                    color: theme.fgColor
                }

                Controls.Label {
                    Layout.alignment: Qt.AlignRight
                    Layout.rightMargin: Mycroft.Units.gridUnit * 2
                    font.pixelSize: 35
                    font.bold: true
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                    text: formatTime(playerDuration)
                    color: theme.fgColor
                }
            }
        }

        Rectangle {
            id: sliderContainer
            width: parent.width
            anchors.bottom: parent.bottom
            height: Mycroft.Units.gridUnit * 2
            color: "transparent"

            T.Slider {
                id: seekableslider
                from: 0.0
                to: playerDuration
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: Mycroft.Units.gridUnit * 2
                property bool sync: false
                live: false
                visible: media.length !== -1 ? 1 : 0
                enabled: media.length !== -1 ? 1 : 0
                value: playerPosition

                handle: Item {
                    x: seekableslider.visualPosition / (parent.width + Mycroft.Units.gridUnit * 2) * parent.width ** 2
                    // The above calculation is to account for the size of the positionMarker
                    anchors.verticalCenter: parent.verticalCenter
                    height: Mycroft.Units.gridUnit * 2

                    Rectangle {
                        id: positionMarker
                        visible: isStreaming
                        enabled: isStreaming
                        anchors.verticalCenter: parent.verticalCenter
                        implicitWidth: Mycroft.Units.gridUnit * 2
                        implicitHeight: Mycroft.Units.gridUnit * 2
                        radius: 100
                        color: seekableslider.pressed ? "#f0f0f0" : "#f6f6f6"
                        border.color: theme.fgColor
                    }
                }

                background: Rectangle {
                    id: sliderBackground
                    x: seekableslider.leftPadding
                    y: seekableslider.topPadding + seekableslider.availableHeight / 2 - height / 2
                    width: seekableslider.availableWidth
                    height: Mycroft.Units.gridUnit * 2
                    radius: Mycroft.Units.gridUnit
                    color: Qt.darker("#22A7F0")
                }
            }
        }
    }
}
