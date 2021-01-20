"""Constants for the MasterLink Gateway integration."""

DOMAIN = "mlgw"
MLGW_GATEWAY = "MLGW_GATEWAY"
MLGW_DEVICES = "MLGW_DEVICES"


# ########################################################################################
# ##### Events

MLGW_EVENT_ML_TELEGRAM = f"{DOMAIN}.ML_telegram"
MLGW_EVENT_MLGW_TELEGRAM = f"{DOMAIN}.MLGW_telegram"

# ########################################################################################
# ##### Configuration contants


CONF_MLGW_DEFAULT_SOURCE = "default_source"
CONF_MLGW_AVAILABLE_SOURCES = "available_sources"
MLGW_DEFAULT_SOURCE = "A.MEM"
MLGW_AVAILABLE_SOURCES = ["CD", "RADIO", "A.MEM"]

CONF_MLGW_DEVICE_NAME = "name"
CONF_MLGW_DEVICE_MLN = "mln"
CONF_MLGW_DEVICE_ROOM = "room"
# this is an undocumented feature of the MasterLink Gateway that provides complete access to the ML data bus,
# so that the integration can listen to all events running on the bus and provide enhanced functionality.
# if you decide to use it, then Username must be 'admin' and password must be the admin password.
CONF_MLGW_USE_MLLOG = "use_mllog"

# ########################################################################################
# ##### MasterLink (not MLGW)  Protocol packet constants

ml_telegram_type_dict = dict(
    [
        (0x0A, "COMMAND"),
        (0x0B, "REQUEST"),
        (0x14, "STATUS"),
        (0x2C, "INFO"),
        (0x40, "TIME"),
        (0x3C, "TIMER"),
        (0x5E, "CONFIG"),
    ]
)

ml_command_type_dict = dict(
    [
        (0x04, "MASTER_PRESENT"),
        (0x06, "DISPLAY_SOURCE"),
        (0x08, "AUDIO_BUS"),  # subtypes seen 01:request status 04:status_distributing 06:status_not_distributing (len 04 or 05)
        (0x0B, "META_DATA"),
        (0x0D, "BEO4_KEY"),
        (0x10, "STANDBY"),
        (0x11, "RELEASE"),
        (0x20, "MLGW_REMOTE_BEO4"),
        (0x30, "WHAT_AUDIO_SOURCE"),  # subtypes seen 02:request 04:response
        (0x3C, "TIMER"),
        (0x40, "CLOCK"),
        (0x44, "TRACK_INFO"),
        (0x45, "GOTO_SOURCE"),
        (0x5C, "REQUEST_KEY"),
        (0x6C, "DISTRIBUTION_REQUEST"),
        (0x82, "TRACK_INFO_LONG"),
        (0x87, "STATUS_INFO"),
        (0x94, "DVD_STATUS_INFO"),
        (0x96, "PC_PRESENT"),
        (0x98, "PICTURE_STATUS_INFO"),
        # more packets that we see on the bus, with a guess of the type
        #(
        #    0x06,
        #    "DISPLAY_SOURCE",
        #),  # Message sent with a payload showing the displayed source name. subtype 3 has the printable source name starting at byte 10 of teh payload
        #(
        #    0x0B,
        #    "EXTENDED_SOURCE_INFORMATION",
        #),  # message sent with 6 subtypes showing information about the source. printable info at byte 14 of the payload subtypes seen: 1: ?? 2: genre 3: country 4: RDS info 5: "NESSUNO" 6: "Unknown"
        #(0x98, "PICTURE_STATUS_INFO"),
    ]
)

ml_command_type_request_key_subtype_dict = dict(
    [
        (0x01, "Request Key"),
        (0x02, "Transfer Key"),
        (0x04, "Key Received"),
        (0xFF, "Undefined"),
    ]
)

ml_state_dict = dict(
    [
        (0x00, "UNKNOWN"),
        (0x01, "STOP"),
        (0x02, "PLAYING"),
        (0x03, "FASTFORWARD"),
        (0x04, "REWIND"),
        (0x05, "RECORD_LOCK"),
        (0x06, "STANDBY"),
        (0x07, "LOAD"),
        (0x08, "STIL_PICTURE"),
        (0x14, "SCAN_FORWARD"),
        (0x15, "SCAN_REVERSE"),
        (0xFF, "BLANK_STATUS"),
    ]
)

ml_pictureformatdict = dict(
    [
        (0x00, "Not known"),
        (0x01, "Known by decoder"),
        (0x02, "4:3"),
        (0x03, "16:9"),
        (0x04, "4:3 Letterbox middle"),
        (0x05, "4:3 Letterbox top"),
        (0x06, "4:3 Letterbox bottom"),
        (0xFF, "Blank picture"),
    ]
)

ml_destselectordict = dict(
    [
        (0x00, "Video Source"),
        (0x01, "Audio Source"),
        (0x05, "V.TAPE/V.MEM"),
        (0x0F, "All Products"),
        (0x1B, "MLGW"),
    ]
)

reverse_ml_destselectordict = {v.upper(): k for k, v in ml_destselectordict.items()}


ml_selectedsourcedict = dict(
    [
        (0x00, "NONE"),
        (0x0B, "TV"),
        (0x15, "V.MEM"),
        (0x16, "DVD_2"),
        (0x1F, "DTV"),
        (0x29, "DVD"),
        (0x33, "V_AUX"),
        (0x3E, "V_AUX2"),
        (0x47, "PC"),
        (0x6F, "RADIO"),
        (0x79, "A.MEM"),
        (0x7A, "N.MUSIC"),
        (0x8D, "CD"),
        (0x97, "A_AUX"),
        (0xA1, "N.RADIO"),
        #  Dummy for 'Listen for all sources'
        (0xFE, "<ALL>"),  # have also seen 0xFF as "all"
    ]
)

reverse_ml_selectedsourcedict = {v.upper(): k for k, v in ml_selectedsourcedict.items()}

beo4_commanddict = dict(
    [
        # Source selection:
        (0x0C, "Standby"),
        (0x47, "Sleep"),
        (0x80, "TV"),
        (0x81, "Radio"),
        (0x82, "DTV2"),
        (0x83, "Aux_A"),
        (0x85, "V.Mem"),
        (0x86, "DVD"),
        (0x87, "Camera"),
        (0x88, "Text"),
        (0x8A, "DTV"),
        (0x8B, "PC"),
        (0x0D, "Doorcam"),
        (0x91, "A.Mem"),
        (0x92, "CD"),
        (0x93, "N.Radio"),
        (0x94, "N.Music"),
        (0x97, "CD2"),
        (0x96, "Spotify"),
        (0xBF, "AV"),
        # Digits:
        (0x00, "Digit-0"),
        (0x01, "Digit-1"),
        (0x02, "Digit-2"),
        (0x03, "Digit-3"),
        (0x04, "Digit-4"),
        (0x05, "Digit-5"),
        (0x06, "Digit-6"),
        (0x07, "Digit-7"),
        (0x08, "Digit-8"),
        (0x09, "Digit-9"),
        # Source control:
        (0x1E, "STEP_UP"),
        (0x1F, "STEP_DW"),
        (0x32, "REWIND"),
        (0x33, "RETURN"),
        (0x34, "WIND"),
        (0x35, "Go / Play"),
        (0x36, "Stop"),
        (0xD4, "Yellow"),
        (0xD5, "Green"),
        (0xD8, "Blue"),
        (0xD9, "Red"),
        # Sound and picture control
        (0x0D, "Mute"),
        (0x1C, "P.Mute"),
        (0x2A, "Format"),
        (0x44, "Sound / Speaker"),
        (0x5C, "Menu"),
        (0x60, "Volume UP"),
        (0x64, "Volume DOWN"),
        (0xDA, "Cinema_On"),
        (0xDB, "Cinema_Off"),
        # Other controls:
        (0x14, "BACK"),
        (0x7F, "Exit"),
        # Continue functionality:
        (0x70, "Rewind Repeat"),
        (0x71, "Wind Repeat"),
        (0x72, "Step_UP Repeat"),
        (0x73, "Step_DW Repeat"),
        (0x75, "Go Repeat"),
        (0x76, "Green Repeat"),
        (0x77, "Yellow Repeat"),
        (0x78, "Blue Repeat"),
        (0x79, "Red Repeat"),
        (0x7E, "Key Release"),
        # Functions:
        (0x40, "Guide"),
        (0x43, "Info"),
        # Cursor functions:
        (0x13, "SELECT"),
        (0xCA, "Cursor_Up"),
        (0xCB, "Cursor_Down"),
        (0xCC, "Cursor_Left"),
        (0xCD, "Cursor_Right"),
        #
        (0x9B, "Light"),
        (0x9C, "Command"),
        # Light Timeout
        (0x58, "Light Timeout"),
        #  Dummy for 'Listen for all commands'
        (0xFF, "<all>"),
    ]
)

BEO4_CMDS = {v.upper(): k for k, v in beo4_commanddict.items()}


# ########################################################################################
# ##### MLGW Protocol packet constants

mlgw_payloadtypedict = dict(
    [
        (0x01, "Beo4 Command"),
        (0x02, "Source Status"),
        (0x03, "Pict&Snd Status"),
        (0x04, "Light and Control command"),
        (0x05, "All standby notification"),
        (0x06, "BeoRemote One control command"),
        (0x07, "BeoRemote One source selection"),
        (0x20, "MLGW virtual button event"),
        (0x30, "Login request"),
        (0x31, "Login status"),
        (0x32, "Change password request"),
        (0x33, "Change password response"),
        (0x34, "Secure login request"),
        (0x36, "Ping"),
        (0x37, "Pong"),
        (0x38, "Configuration change notification"),
        (0x39, "Request Serial Number"),
        (0x3A, "Serial Number"),
        (0x40, "Location based event"),
    ]
)

MLGW_PL = {v.upper(): k for k, v in mlgw_payloadtypedict.items()}


mlgw_virtualactiondict = dict([(0x01, "PRESS"), (0x02, "HOLD"), (0x03, "RELEASE")])

mlgw_sourceactivitydict = dict(
    [
        (0x00, "Unknown"),
        (0x01, "Stop"),
        (0x02, "Playing"),
        (0x03, "Wind"),
        (0x04, "Rewind"),
        (0x05, "Record lock"),
        (0x06, "Standby"),
    ]
)

### for '0x03: Picture and Sound Status'
mlgw_soundstatusdict = dict([(0x00, "Not muted"), (0x01, "Muted")])

reverse_mlgw_soundstatusdict = {v.upper(): k for k, v in mlgw_soundstatusdict.items()}

mlgw_speakermodedict = dict(
    [
        (0x01, "Center channel"),
        (0x02, "2ch stereo"),
        (0x03, "Front surround"),
        (0x04, "4ch stereo"),
        (0x05, "Full surround"),
        #  Dummy for 'Listen for all modes'
        (0xFD, "<all>"),
    ]
)

reverse_mlgw_speakermodedict = {v.upper(): k for k, v in mlgw_speakermodedict.items()}

mlgw_screenmutedict = dict([(0x00, "not muted"), (0x01, "muted")])

mlgw_screenactivedict = dict([(0x00, "not active"), (0x01, "active")])

mlgw_cinemamodedict = dict([(0x00, "Cinemamode=off"), (0x01, "Cinemamode=on")])

mlgw_stereoindicatordict = dict([(0x00, "Mono"), (0x01, "Stereo")])

### for '0x04: Light and Control command'
mlgw_lctypedict = dict([(0x01, "LIGHT"), (0x02, "CONTROL")])

### for '0x31: Login Status
mlgw_loginstatusdict = dict([(0x00, "OK"), (0x01, "FAIL")])
