import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material

import org.electrum 1.0

import "controls"

ElDialog {
    id: rootItem

    title: qsTr('Nostr relays')
    iconSource: Qt.resolvedUrl('../../icons/nostr.png')

    width: parent.width
    height: parent.height

    padding: 0

    property bool valid: true

    function clean_array(text) {
        var relays = []
        const fragments = text.split("\n")
        fragments.forEach(function(fragment) {
            fragment = fragment.trim()
            if (fragment != "" && !relays.includes(fragment))
                relays.push(fragment)
        })
        return relays
    }

    function verify(text) {
        const re=/^wss?:\/\/([a-zA-Z0-9\-]+\.)+[a-zA-Z]+(\/.*)?$/
        const relays = clean_array(text)
        var isvalid = relays.every(function(relay) {
            return re.test(relay)
        })
        return isvalid
    }

    ColumnLayout {
        width: parent.width
        height: parent.height
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: constants.paddingLarge
            Layout.rightMargin: constants.paddingLarge

            RowLayout {
                Layout.fillWidth: true
                TextHighlightPane {
                    Layout.fillWidth: true
                    Label {
                        text: qsTr('Enter the list of Nostr relays')
                        width: parent.width
                        wrapMode: Text.Wrap
                    }
                }
                HelpButton {
                    heading: Config.shortDescFor('NOSTR_RELAYS')
                    helptext: Config.longDescFor('NOSTR_RELAYS')
                }
            }

            RowLayout {
                Layout.fillWidth: true
                ElTextArea {
                    id: relays_ta
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    font.family: FixedFont
                    wrapMode: TextEdit.WrapAnywhere
                    onTextChanged: valid = verify(text)
                    inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                    background: PaneInsetBackground {
                        baseColor: constants.darkerDialogBackground
                    }
                }
                ColumnLayout {
                    Layout.alignment: Qt.AlignTop
                    ToolButton {
                        icon.source: '../../icons/paste.png'
                        icon.height: constants.iconSizeMedium
                        icon.width: constants.iconSizeMedium
                        onClicked: {
                            if (verify(AppController.clipboardToText())) {
                                if (!relays_ta.text.endsWith('\n'))
                                    relays_ta.text = relays_ta.text + '\n'
                                relays_ta.text = relays_ta.text + AppController.clipboardToText()
                            }
                        }
                    }
                }
            }
        }

        FlatButton {
            Layout.fillWidth: true
            text: qsTr('Ok')
            enabled: valid
            icon.source: '../../icons/confirmed.png'
            onClicked: {
                Config.nostrRelays = clean_array(relays_ta.text).join(",")
                rootItem.close()
            }
        }
    }


    Component.onCompleted: {
        relays_ta.text = Config.nostrRelays.replace(/,/g, "\n")
    }
}
