"""The gateway to interact with a Bang & Olufsen MasterLink Gateway or BeoLink Gateway. """
import asyncio
from datetime import datetime
import logging

import telnetlib
import socket
import threading
import time

from homeassistant.core import HassJob, callback, HomeAssistant
from homeassistant.const import STATE_OFF, STATE_ON, EVENT_HOMEASSISTANT_STOP

from .const import (
    DOMAIN,
    beo4_commanddict,
    ml_selectedsourcedict,
    reverse_ml_selectedsourcedict,
    ml_destselectordict,
    ml_pictureformatdict,
    ml_state_dict,
    ml_telegram_type_dict,
    ml_command_type_dict,
    mlgw_payloadtypedict,
    mlgw_virtualactiondict,
    mlgw_sourceactivitydict,
    mlgw_soundstatusdict,
    mlgw_speakermodedict,
    reverse_mlgw_speakermodedict,
    mlgw_screenmutedict,
    mlgw_screenactivedict,
    mlgw_cinemamodedict,
    mlgw_stereoindicatordict,
    mlgw_lctypedict,
    mlgw_loginstatusdict,
    BEO4_CMDS,
    MLGW_PL,
    MLGW_EVENT_ML_TELEGRAM,
    MLGW_EVENT_MLGW_TELEGRAM,
)

_LOGGER = logging.getLogger(__name__)


class MasterLinkGateway:
    """Masterlink gateway to interact with a MasterLink Gateway http://mlgw.bang-olufsen.dk/source/documents/mlgw_2.24b/MlgwProto0240.pdf ."""

    def __init__(
        self, host, port, user, password, default_source, available_sources, hass
    ):
        """Initialize the MLGW gateway."""
        # for both connections
        self._host = host
        self._user = user
        self._password = password
        # for the ML (Telnet CLI) connection
        self._connectedML = False
        self._tn = None
        # for the MLGW (Port 9000) connection
        self._port = port
        self._socket = None
        self.buffersize = 1024
        self._connectedMLGW = False
        self.stopped = threading.Event()
        # to manage the sources and devices
        self._beolink_source = default_source
        self._available_sources = available_sources
        self._devices = None
        self._hass: HomeAssistant = hass
        self._serial = None

    @property
    def connectedMLGW(self):
        return self._connectedMLGW

    # return the latest known active source
    @property
    def beolink_source(self):
        return self._beolink_source

    @property
    def available_sources(self):
        return self._available_sources

    def ml_connect(self):
        _LOGGER.info("Trying to connect to ML CLI: %s" % (self._host))
        self._connectedML = False

        try:
            self._tn = telnetlib.Telnet(self._host)

            line = self._tn.read_until(b"login: ", 3)
            if line[-7:] != b"login: ":
                _LOGGER.debug("Unexpected login prompt: %s" % (line))
                raise ConnectionError
            self._tn.write(self._password.encode("ascii") + b"\n")

            #            line = self._tn.read_until(
            #                b"Logged in", 3
            #            )  # The first line says "Logged In"
            #            if line[-9:] != b"Logged in":
            #                _LOGGER.debug("Password Response was: %s" % (line))
            #                raise ConnectionError

            line = self._tn.read_until(
                b"MLGW >", 10
            )  # the third line should be the prompt
            if line[-6:] != b"MLGW >":
                _LOGGER.debug("Unexpected CLI prompt: %s" % (line))
                raise ConnectionError

            # Enter the undocumented Masterlink Logging function
            self._tn.write(b"_MLLOG ONLINE\r\n")
            #            self._hass.async_create_task(self._ml_thread())
            threading.Thread(target=self._ml_thread).start()

            self._connectedML = True
            _LOGGER.info("Connected to ML CLI: %s" % (self._host))

            return True

        except EOFError as exc:
            _LOGGER.error("Error opening ML CLI connection to: %s", exc)
            return False

        except ConnectionError:
            _LOGGER.error("Failed to connect, continuing without ML CLI")
            return False

    ## Open tcp connection to mlgw
    def mlgw_connect(self):
        _LOGGER.info("Trying to connect to MLGW")
        self._connectedMLGW = False

        # open socket to masterlink gateway
        self._socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._recvtimeout = 5  # timeout recv every 5 seconds
        self._lastping = 0  # last ping will say how many seconds ago was the last ping.
        self._socket.settimeout(self._recvtimeout)
        try:
            self._socket.connect((self._host, self._port))
        except Exception as e:
            self._socket = None
            _LOGGER.error("Error opening MLGW connection to %s: %s" % (self._host, e))
            return

        #        self._hass.async_create_task(self._mlgw_listen_thread())
        threading.Thread(target=self._mlgw_listen_thread).start()

        self._connectedMLGW = True
        self.mlgw_ping()  # force a ping so that the MLGW will request authentication
        _LOGGER.info(
            "Opened connection to ML Gateway to %s port: %s"
            % (self._host, str(self._port))
        )

    def ml_close(self):
        if self._connectedML:
            self._connectedML = False
            #            self.stopped.set()
            try:
                print(self._tn.eof)
                print(self._tn)
                self._tn.close()
            except:
                _LOGGER.error("Error closing ML CLI")
            _LOGGER.warning("Closed connection to ML CLI")

    # This is the thread function to manage the ML CLI connection
    # async def _ml_thread(self):
    def _ml_thread(self):
        """Receive notification about incoming event from the ML connection."""

        input_bytes = ""
        while not self.stopped.isSet():
            try:  # nonblocking read from the connection
                input_bytes = input_bytes + self._tn.read_very_eager().decode("ascii")
            except EOFError:
                _LOGGER.error("ML CLI Thread: EOF Error ")
                self.ml_close()
                return

            if input_bytes.find("\n") > 0:  # if there is a full line

                line = input_bytes[0 : input_bytes.find("\n")]
                input_bytes = input_bytes[input_bytes.find("\n") + 1 :]

                items = line.split()
                try:
                    date_time_obj = datetime.strptime(items[0], "%Y%m%d-%H:%M:%S:%f:")
                    telegram = bytearray()

                    for x in range(1, len(items)):
                        telegram.append(int(items[x][:-1], base=16))

                    encoded_telegram = decode_ml_to_dict(telegram)
                    encoded_telegram["timestamp"] = date_time_obj.isoformat()
                    encoded_telegram["bytes"] = "".join(
                        "{:02x}".format(x) for x in telegram
                    )
                    _LOGGER.debug("Processing telegram: %s", encoded_telegram)

                    # try to find the mln of the from_device and to_device
                    if self._devices is not None:
                        for x in self._devices:
                            if x._ml == encoded_telegram["from_device"]:
                                encoded_telegram["from_mln"] = x._mln
                            if x._ml == encoded_telegram["to_device"]:
                                encoded_telegram["to_mln"] = x._mln

                    # if a GOTO Source telegram is received, set the beolink source to it
                    if encoded_telegram["payload_type"] == "GOTO_SOURCE":
                        self._beolink_source = encoded_telegram["payload"]["source"]

                    self._hass.add_job(
                        self._notify_incoming_ML_telegram, encoded_telegram
                    )
                except ValueError:
                    continue
            else:  # else sleep a bit and then continue reading
                time.sleep(0.5)

        self.ml_close()

    @callback
    def _notify_incoming_ML_telegram(self, telegram):
        """Notify hass when an incoming ML message is received."""
        self._hass.bus.async_fire(MLGW_EVENT_ML_TELEGRAM, telegram)

    @callback
    def _notify_incoming_MLGW_telegram(self, telegram):
        """Notify hass when an incoming ML message is received."""
        self._hass.bus.async_fire(MLGW_EVENT_MLGW_TELEGRAM, telegram)

    # populate the list of devices configured on the gateway.
    def set_devices(self, devices):
        self._devices = devices

    ## Login
    def mlgw_login(self):
        _LOGGER.info("Trying to login")
        if self._connectedMLGW:
            wrkstr = self._user + chr(0x00) + self._password
            payload = bytearray()
            for c in wrkstr:
                payload.append(ord(c))
            self.mlgw_send(0x30, payload)  # login Request

    def mlgw_ping(self):
        _LOGGER.debug("ping")
        self.mlgw_send(0x36, "")

    ## Close connection to mlgw
    def mlgw_close(self):
        if self._connectedMLGW:
            self._connectedMLGW = False
            self.stopped.set()
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            except:
                _LOGGER.warning("Error closing connection to ML Gateway")
                return
            _LOGGER.info("Closed connection to ML Gateway")

    ## Send command to mlgw
    def mlgw_send(self, msg_type, payload):
        if self._connectedMLGW:
            self._telegram = bytearray()
            self._telegram.append(0x01)  # byte[0] SOH
            self._telegram.append(msg_type)  # byte[1] msg_type
            self._telegram.append(len(payload))  # byte[2] Length
            self._telegram.append(0x00)  # byte[3] Spare
            for p in payload:
                self._telegram.append(p)
            self._socket.sendall(self._telegram)

            _LOGGER.debug(
                "mlgw: >SENT: "
                + _getpayloadtypestr(msg_type)
                + ": "
                + _getpayloadstr(self._telegram)
            )  # debug

            # Sleep to allow msg to arrive
            time.sleep(1)

    ## Send Beo4 command to mlgw
    def mlgw_send_beo4_cmd(self, mln, dest, cmd):
        self._payload = bytearray()
        self._payload.append(mln)  # byte[0] MLN
        self._payload.append(dest)  # byte[1] Dest-Sel (0x00, 0x01, 0x05, 0x0f)
        self._payload.append(cmd)  # byte[2] Beo4 Command
        self._payload.append(0x00)  # byte[3] Sec-Source
        self._payload.append(0x00)  # byte[3] Link
        self.mlgw_send(0x01, self._payload)

    ## Send Beo4 commmand and store the source name
    def mlgw_send_beo4_cmd_select_source(self, mln, dest, source):
        self._beolink_source = source
        self.mlgw_send_beo4_cmd(mln, dest, BEO4_CMDS.get(source))

    def mlgw_send_virtual_btn_press(self, btn):
        self.mlgw_send(0x20, [btn])

    ## Get serial number of mlgw
    def mlgw_get_serial(self):
        if self._connectedMLGW:
            # Request serial number
            self.mlgw_send(MLGW_PL.get("REQUEST SERIAL NUMBER"), "")
            (_, self._serial) = self.mlgw_receive()
            _LOGGER.warning(
                "mlgw: Serial number of ML Gateway is " + self._serial
            )  # info
        return

    # This is the thread function to manage the MLGW connection
    def _mlgw_listen_thread(self):
        while not self.stopped.isSet():
            response = None
            try:
                response = self._socket.recv(self.buffersize)
            except KeyboardInterrupt:
                _LOGGER.warning("mlgw: keyboard interrupt in listen thread")
                self.mlgw_close()
            except socket.timeout:
                self._lastping = self._lastping + self._recvtimeout
                # Ping the gateway to test the connection every 10 minutes
                if self._lastping >= 600:
                    self.mlgw_ping()
                    self._lastping = 0
                continue

            if response is not None and response != b"":
                # Decode response. Response[0] is SOH, or 0x01
                msg_byte = response[1]
                msg_type = _getpayloadtypestr(msg_byte)
                msg_payload = _getpayloadstr(response)

                _LOGGER.debug(f"mlgw: Msg type: {msg_type}. Payload: {msg_payload}")

                if msg_byte == 0x20:  # Virtual Button event
                    virtual_btn = response[4]
                    if len(response) < 5:
                        virtual_action = _getvirtualactionstr(0x01)
                    else:
                        virtual_action = _getvirtualactionstr(response[5])
                    _LOGGER.info(
                        f"mlgw: Virtual button pressed: button {virtual_btn} action {virtual_action}"
                    )
                    decoded = dict()
                    decoded["payload_type"] = "virtual_button"
                    decoded["button"] = virtual_btn
                    decoded["action"] = virtual_action
                    self._hass.add_job(self._notify_incoming_MLGW_telegram, decoded)

                elif msg_byte == 0x31:  # Login Status
                    if msg_payload == "FAIL":
                        _LOGGER.info("mlgw: Login needed")
                        self.mlgw_login()
                    elif msg_payload == "OK":
                        _LOGGER.info("mlgw: Login successful")
                        self.mlgw_get_serial()

                elif msg_byte == 0x37:  # Pong (Ping response)
                    _LOGGER.debug("mlgw: pong")

                elif msg_byte == 0x02:  # Source status
                    _LOGGER.info(f"mlgw: Msg type: {msg_type}. Payload: {msg_payload}")
                    sourceMLN = _getmlnstr(response[4])
                    beolink_source = _getselectedsourcestr(response[5]).upper()
                    sourceMediumPosition = _hexword(response[6], response[7])
                    sourcePosition = _hexword(response[8], response[9])
                    sourceActivity = _getdictstr(mlgw_sourceactivitydict, response[10])
                    pictureFormat = _getdictstr(ml_pictureformatdict, response[11])
                    decoded = dict()
                    decoded["payload_type"] = "source_status"
                    decoded["source_mln"] = sourceMLN
                    decoded["source"] = beolink_source
                    decoded["source_medium_position"] = sourceMediumPosition
                    decoded["source_position"] = sourcePosition
                    decoded["source_activity"] = sourceActivity
                    decoded["picture_format"] = pictureFormat
                    self._hass.add_job(self._notify_incoming_MLGW_telegram, decoded)
                    if sourceActivity == "Playing":
                        self._beolink_source = beolink_source

                elif msg_byte == 0x03:  # Source status
                    _LOGGER.info(f"mlgw: Msg type: {msg_type}. Payload: {msg_payload}")
                    decoded = dict()
                    decoded["payload_type"] = "pict_sound_status"
                    decoded["source_mln"] = _getmlnstr(response[4])
                    decoded["sound_status"] = _getdictstr(
                        mlgw_soundstatusdict, response[5]
                    )
                    decoded["speaker_mode"] = _getdictstr(
                        mlgw_speakermodedict, response[6]
                    )
                    decoded["volume"] = int(response[7])
                    decoded["screen1_mute"] = _getdictstr(
                        mlgw_screenmutedict, response[8]
                    )
                    decoded["screen1_active"] = _getdictstr(
                        mlgw_screenactivedict, response[9]
                    )
                    decoded["screen2_mute"] = _getdictstr(
                        mlgw_screenmutedict, response[10]
                    )
                    decoded["screen2_active"] = _getdictstr(
                        mlgw_screenactivedict, response[11]
                    )
                    decoded["cinema_mode"] = _getdictstr(
                        mlgw_cinemamodedict, response[12]
                    )
                    decoded["stereo_mode"] = _getdictstr(
                        mlgw_stereoindicatordict, response[13]
                    )
                    self._hass.add_job(self._notify_incoming_MLGW_telegram, decoded)

                elif msg_byte == 0x05:  # All Standby
                    _LOGGER.info(f"mlgw: Msg type: {msg_type}. Payload: {msg_payload}")
                    if self._devices is not None:
                        # set all connected devices state to off
                        for i in self._devices:
                            i.set_state(STATE_OFF)
                    decoded = dict()
                    decoded["payload_type"] = "all_standby"
                    self._hass.add_job(self._notify_incoming_MLGW_telegram, decoded)

                elif msg_byte == 0x04:  # Light / Control command
                    lcroom = _getroomstr(response[4])
                    lctype = _getdictstr(mlgw_lctypedict, response[5])
                    lccommand = _getbeo4commandstr(response[6])
                    _LOGGER.info(
                        f"mlgw: Light/Control command: room: {lcroom} type: {lctype} command {lccommand}"
                    )
                    decoded = dict()
                    decoded["payload_type"] = "light_control_event"
                    decoded["room"] = response[4]
                    decoded["type"] = lctype
                    decoded["command"] = lccommand
                    self._hass.add_job(self._notify_incoming_MLGW_telegram, decoded)

                else:
                    _LOGGER.info(f"mlgw: Msg type: {msg_type}. Payload: {msg_payload}")

        self.mlgw_close()

    ## Receive message from mlgw
    def mlgw_receive(self):
        if self._connectedMLGW:
            try:
                self._mlgwdata = self._socket.recv(self.buffersize)
            except socket.timeout:
                pass
            except KeyboardInterrupt:
                _LOGGER.error("mlgw: KeyboardInterrupt, terminating...")
                self.mlgw_close()

            self._payloadstr = _getpayloadstr(self._mlgwdata)
            if self._mlgwdata[0] != 0x01:
                _LOGGER.error("mlgw: Received telegram with SOH byte <> 0x01")
            if self._mlgwdata[3] != 0x00:
                _LOGGER.error("mlgw: Received telegram with spare byte <> 0x00")
            _LOGGER.debug(
                "mlgw: <RCVD: '"
                + _getpayloadtypestr(self._mlgwdata[1])
                + "': "
                + str(self._payloadstr)
            )  # debug
            return (self._mlgwdata[1], str(self._payloadstr))


# ########################################################################################
# ##### Create the gateway instance and set up listners to destroy it if needed


async def create_mlgw_gateway(
    host,
    port,
    user,
    password,
    default_source,
    available_sources,
    use_mllog,
    hass: HomeAssistant,
):
    """Create the mlgw gateway."""
    gateway = MasterLinkGateway(
        host, port, user, password, default_source, available_sources, hass
    )

    if use_mllog == True:
        gateway.ml_connect()

    gateway.mlgw_connect()

    def _stop_listener(_event):
        gateway.stopped.set()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_listener)

    return gateway


# ########################################################################################
# ##### Utility functions


def _hexbyte(byte):
    resultstr = hex(byte)
    if byte < 16:
        resultstr = resultstr[:2] + "0" + resultstr[2]
    return resultstr


def _hexword(byte1, byte2):
    resultstr = _hexbyte(byte2)
    resultstr = _hexbyte(byte1) + resultstr[2:]
    return resultstr


def _dictsanitize(d, s):
    result = d.get(s)
    if result == None:
        result = "UNKNOWN (type=" + _hexbyte(s) + ")"
    return str(result)


# ########################################################################################
# ##### Decode Masterlink Protocol packet to readable string


def decode_ml_to_string(telegram):
    decoded = (
        decode_device(telegram[1])
        + " => "
        + decode_device(telegram[0])
        + " TYPE: "
        + _dictsanitize(ml_telegram_type_dict, telegram[3])
        + " SRC_DEST:"
        + _hexbyte(telegram[4])
        + " ORIG_SRC:"
        + _hexbyte(telegram[5])
        + " PL_Type: "
        + _dictsanitize(ml_command_type_dict, telegram[7])
        + " Len: "
        + str(telegram[8])
    )
    # status info
    if telegram[7] == 0x87:
        decoded = (
            decoded
            + " Source: "
            + _dictsanitize(ml_selectedsourcedict, telegram[10])
            + " Ch/Track: "
            + str(telegram[19])
            + " Activity: "
            + _dictsanitize(ml_state_dict, telegram[21])
            + " Source Medium: "
            + str(_hexword(telegram[18], telegram[17]))
            + " Picture Identifier: "
            + _dictsanitize(ml_pictureformatdict, telegram[23])
        )
    # beo4 command
    if telegram[7] == 0x0D:
        decoded = (
            decoded
            + " Source: "
            + _dictsanitize(ml_selectedsourcedict, telegram[10])
            + " Command: "
            + _dictsanitize(beo4_commanddict, telegram[11])
        )
    # track info long
    if telegram[7] == 0x82:
        decoded = (
            decoded
            + " Source: "
            + _dictsanitize(ml_selectedsourcedict, telegram[11])
            + " Ch/Track: "
            + str(telegram[12])
            + " Activity: "
            + _dictsanitize(ml_state_dict, telegram[13])
        )
    # track info
    if telegram[7] == 0x44:
        if telegram[9] == 0x07:
            decoded = (
                decoded
                + " Switch Source. Old: "
                + _dictsanitize(ml_selectedsourcedict, telegram[11])
                + " New: "
                + _dictsanitize(ml_selectedsourcedict, telegram[22])
            )
        elif telegram[9] == 0x05:
            decoded = (
                decoded
                + " Current Source: "
                + _dictsanitize(ml_selectedsourcedict, telegram[11])
            )
        else:
            decoded = decoded + " Undefined"
    # goto source
    if telegram[7] == 0x45:
        decoded = (
            decoded
            + " Source: "
            + _dictsanitize(ml_selectedsourcedict, telegram[11])
            + " Ch/Track: "
            + str(telegram[12])
        )
    # remote request
    if telegram[7] == 0x20:
        decoded = (
            decoded
            + " Command: "
            + _dictsanitize(beo4_commanddict, telegram[14])
            + " Dest Selector: "
            + _dictsanitize(ml_destselectordict, telegram[11])
        )
    # request_key
    if telegram[7] == 0x5C:
        if telegram[9] == 0x01:
            decoded = decoded + " Request Key"
        elif telegram[9] == 0x02:
            decoded = decoded + " Transfter Key"
        elif telegram[9] == 0x04:
            decoded = decoded + " Key Received"
        else:
            decoded = decoded + " Undefined"
    # what audio source
    if telegram[7] == 0x30:
        if telegram[8] == 0x0:
            decoded = decoded + " Request Audio Source"
        elif telegram[8] == 0x02:
            decoded = (
                decoded
                + " Audio Source: "
                + _dictsanitize(ml_selectedsourcedict, telegram[11])
            )
        else:
            decoded = decoded + " Undefined"
    return decoded


def decode_device(d):
    if d == 0xC0:
        return "VIDEO_MASTER"
    if d == 0xC1:
        return "AUDIO_MASTER"
    if d == 0xC2:
        return "SLAVE_DEVICE"
    if d == 0x83:
        return "ALL_LINK_DEVICES"
    if d == 0x80:
        return "ALL"
    if d == 0xF0:
        return "MLGW"
    else:
        return hex(d)


# ########################################################################################
# ##### Decode Masterlink Protocol packet to a serializable dict


def decode_ml_to_dict(telegram):
    decoded = dict()
    decoded["from_device"] = decode_device(telegram[1])
    decoded["to_device"] = decode_device(telegram[0])
    decoded["type"] = _dictsanitize(ml_telegram_type_dict, telegram[3])
    decoded["src_dest"] = _dictsanitize(ml_selectedsourcedict, telegram[4])
    decoded["orig_src"] = _dictsanitize(ml_selectedsourcedict, telegram[5])
    decoded["payload_type"] = _dictsanitize(ml_command_type_dict, telegram[7])
    decoded["payload_len"] = str(telegram[8])
    decoded["payload"] = dict()

    # status info
    if telegram[7] == 0x87:
        decoded["payload"]["source"] = _dictsanitize(
            ml_selectedsourcedict, telegram[10]
        )
        decoded["payload"]["channel_track"] = str(telegram[19])
        decoded["payload"]["activity"] = _dictsanitize(ml_state_dict, telegram[21])
        decoded["payload"]["source_medium"] = str(_hexword(telegram[18], telegram[17]))
        decoded["payload"]["picture_identifier"] = _dictsanitize(
            ml_pictureformatdict, telegram[23]
        )
    # beo4 command
    if telegram[7] == 0x0D:
        decoded["payload"]["source"] = _dictsanitize(
            ml_selectedsourcedict, telegram[10]
        )
        decoded["payload"]["command"] = _dictsanitize(beo4_commanddict, telegram[11])
    # track info long
    if telegram[7] == 0x82:
        decoded["payload"]["source"] = _dictsanitize(
            ml_selectedsourcedict, telegram[11]
        )
        decoded["payload"]["channel_track"] = str(telegram[12])
        decoded["payload"]["activity"] = _dictsanitize(ml_state_dict, telegram[13])
    # track info
    if telegram[7] == 0x44:
        if telegram[9] == 0x07:
            decoded["payload"]["subtype"] = "Change Source"
            decoded["payload"]["prev_source"] = _dictsanitize(
                ml_selectedsourcedict, telegram[11]
            )
            decoded["payload"]["source"] = _dictsanitize(
                ml_selectedsourcedict, telegram[22]
            )
        elif telegram[9] == 0x05:
            decoded["payload"]["subtype"] = "Current Source"
            decoded["payload"]["source"] = _dictsanitize(
                ml_selectedsourcedict, telegram[11]
            )
        else:
            decoded["payload"]["subtype"] = "Undefined"
    # goto source
    if telegram[7] == 0x45:
        decoded["payload"]["source"] = _dictsanitize(
            ml_selectedsourcedict, telegram[11]
        )
        decoded["payload"]["channel_track"] = str(telegram[12])
    # remote request
    if telegram[7] == 0x20:
        decoded["payload"]["command"] = _dictsanitize(beo4_commanddict, telegram[14])
        decoded["payload"]["dest_selector"] = _dictsanitize(
            ml_destselectordict, telegram[11]
        )
    # request_key
    if telegram[7] == 0x5C:
        if telegram[9] == 0x01:
            decoded["payload"]["subtype"] = "Request Key"
        elif telegram[9] == 0x02:
            decoded["payload"]["subtype"] = "Transfter Key"
        elif telegram[9] == 0x04:
            decoded["payload"]["subtype"] = "Key Received"
        else:
            decoded["payload"]["subtype"] = "Undefined"
    # what audio source
    if telegram[7] == 0x30:
        if telegram[8] == 0x0:
            decoded["payload"]["subtype"] = "Request Audio Source"
        elif telegram[8] == 0x02:
            decoded["payload"]["subtype"] = "Audio Source"
            decoded["payload"]["source"] = _dictsanitize(
                ml_selectedsourcedict, telegram[11]
            )
        else:
            decoded["payload"]["subtype"] = "Undefined"
    return decoded


# ########################################################################################
# ##### Decode MLGW Protocol packet to readable string

## Get decoded string for mlgw packet's payload type
#
def _getpayloadtypestr(payloadtype):
    result = mlgw_payloadtypedict.get(payloadtype)
    if result == None:
        result = "UNKNOWN (type=" + _hexbyte(payloadtype) + ")"
    return str(result)


def _getroomstr(room):
    result = "Room=" + str(room)
    return result


def _getmlnstr(mln):
    result = "MLN=" + str(mln)
    return result


def _getbeo4commandstr(command):
    result = beo4_commanddict.get(command)
    if result == None:
        result = "Cmd=" + _hexbyte(command)
    return result


def _getvirtualactionstr(action):
    result = mlgw_virtualactiondict.get(action)
    if result == None:
        result = "Action=" + _hexbyte(action)
    return result


def _getselectedsourcestr(source):
    result = ml_selectedsourcedict.get(source)
    if result == None:
        result = "Src=" + _hexbyte(source)
    return result


def _getspeakermodestr(source):
    result = mlgw_speakermodedict.get(source)
    if result == None:
        result = "mode=" + _hexbyte(source)
    return result


def _getdictstr(mydict, mykey):
    result = mydict.get(mykey)
    if result == None:
        result = _hexbyte(mykey)
    return result


## Get decoded string for a mlgw packet
#
#   The raw message (mlgw packet) is handed to this function.
#   The result of this function is a human readable string, describing the content
#   of the mlgw packet
#
#  @param message   raw mlgw telegram
#  @returns         telegram as a human readable string
#
def _getpayloadstr(message):
    if message[2] == 0:  # payload length is 0
        resultstr = "[No payload]"
    elif message[1] == 0x01:  # Beo4 Command
        resultstr = _getmlnstr(message[4])
        resultstr = resultstr + " " + _hexbyte(message[5])
        resultstr = resultstr + " " + _getbeo4commandstr(message[6])

    elif message[1] == 0x02:  # Source Status
        resultstr = _getmlnstr(message[4])
        resultstr = resultstr + " " + _getselectedsourcestr(message[5])
        resultstr = resultstr + " " + _hexword(message[6], message[7])
        resultstr = resultstr + " " + _hexword(message[8], message[9])
        resultstr = resultstr + " " + _getdictstr(mlgw_sourceactivitydict, message[10])
        resultstr = resultstr + " " + _getdictstr(ml_pictureformatdict, message[11])

    elif message[1] == 0x03:  # Picture and Sound Status
        resultstr = _getmlnstr(message[4])
        if message[5] != 0x00:
            resultstr = resultstr + " " + _getdictstr(mlgw_soundstatusdict, message[5])
        resultstr = resultstr + " " + _getdictstr(mlgw_speakermodedict, message[6])
        resultstr = resultstr + " Vol=" + str(message[7])
        if message[9] != 0x00:
            resultstr = (
                resultstr + " Scrn:" + _getdictstr(mlgw_screenmutedict, message[8])
            )
        if message[11] != 0x00:
            resultstr = (
                resultstr + " Scrn2:" + _getdictstr(mlgw_screenmutedict, message[10])
            )
        if message[12] != 0x00:
            resultstr = resultstr + " " + _getdictstr(mlgw_cinemamodedict, message[12])
        if message[13] != 0x01:
            resultstr = (
                resultstr + " " + _getdictstr(mlgw_stereoindicatordict, message[13])
            )

    elif message[1] == 0x04:  # Light and Control command
        resultstr = (
            _getroomstr(message[4])
            + " "
            + _getdictstr(mlgw_lctypedict, message[5])
            + " "
            + _getbeo4commandstr(message[6])
        )

    elif message[1] == 0x30:  # Login request
        wrk = message[4 : 4 + message[2]]
        for i in range(0, message[2]):
            if wrk[i] == 0:
                wrk[i] = 0x7F
        wrk = wrk.decode("utf-8")
        resultstr = wrk.split(chr(0x7F))[0] + " / " + wrk.split(chr(0x7F))[1]

    elif message[1] == 0x31:  # Login status
        resultstr = _getdictstr(mlgw_loginstatusdict, message[4])

    elif message[1] == 0x3A:  # Serial Number
        resultstr = message[4 : 4 + message[2]].decode("utf-8")

    else:  # Display raw payload
        resultstr = ""
        for i in range(0, message[2]):
            if i > 0:
                resultstr = resultstr + " "
            resultstr = resultstr + _hexbyte(message[4 + i])
    return resultstr
