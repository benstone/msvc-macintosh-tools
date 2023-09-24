import dataclasses
import datetime
import io
import struct
import zlib

MAX_FILENAME_LEN = 64
MACINTOSH_EPOCH = datetime.datetime(1904, 1, 1)


def to_mac_string(value: str) -> bytes:
    """ Encode a string in the MacRoman character set """
    return value.encode("macroman")


def to_mac_datetime(value: datetime.datetime) -> int:
    """ Convert a date to the number of seconds since 1904/1/1 """
    return int((value - MACINTOSH_EPOCH).total_seconds())


@dataclasses.dataclass
class MacBinaryIIFile:
    file_name: str
    file_type: str
    file_creator: str

    data_fork: bytes = None
    resource_fork: bytes = None

    creation_date: datetime.datetime = None
    modification_date: datetime.datetime = None

    def __post_init__(self):
        """ Set default values and validate """
        if self.creation_date is None:
            self.creation_date = datetime.datetime.now()
        if self.modification_date is None:
            self.modification_date = datetime.datetime.now()

        self.validate()

    def validate(self):
        """ Check fields are valid """
        if len(self.file_name) >= MAX_FILENAME_LEN:
            raise ValueError(f"Filename must be < {MAX_FILENAME_LEN}")

        if len(self.file_type) != 4:
            raise ValueError("File type must be four characters")
        if len(self.file_creator) != 4:
            raise ValueError("File creator must be four characters")

    def write(self, output_file: io.IOBase):
        """ Generate the MacBinary file """

        self.validate()

        # default fields
        finder_flags_upper = 0
        finder_flags_lower = 0
        finder_position = (0, 0)
        folder_id = 0
        protected = 0

        data_fork = self.data_fork if self.data_fork else b''
        rsrc_fork = self.resource_fork if self.resource_fork else b''

        # Ref: http://files.stairways.com/other/macbinaryii-standard-info.txt
        header = struct.pack(">B64p4s4sBB3HBBIIIIHB14sIhBB",
                             # old version number, must be kept at zero for compatibility
                             0,
                             # file name (packed as a pascal string)
                             to_mac_string(self.file_name),
                             # file type (normally expressed as four characters)
                             to_mac_string(self.file_type),
                             # file creator (normally expressed as four characters)
                             to_mac_string(self.file_creator),
                             # original Finder flags
                             finder_flags_upper,
                             # zero fill, must be zero for compatibility
                             0,
                             # file's vertical position within its window
                             finder_position[0],
                             # file's horizontal position within its window
                             finder_position[1],
                             # file's window or folder ID
                             folder_id,
                             # "Protected" flag (in low order bit)
                             protected,
                             # zero fill, must be zero for compatibility
                             0,
                             # data fork length
                             len(data_fork),
                             # resource fork length
                             len(rsrc_fork),
                             # file creation date
                             to_mac_datetime(self.creation_date),
                             # file modification date
                             to_mac_datetime(self.modification_date),
                             # zero fill, must be zero for compatibility
                             0,
                             # Finder Flags, bits 0-7. (Bits 8-15 are already in byte 73)
                             finder_flags_lower,
                             # Padding
                             b'\x00' * 14,
                             # length of total files when packed files are unpacked.
                             0,
                             # Length of a secondary header
                             0,
                             # Version number of Macbinary II that the uploading program is written for
                             # (the version begins at 129)
                             129,
                             # Minimum MacBinary II version needed to read this file
                             129,
                             )

        assert len(header) == 124
        header_crc = zlib.crc32(header)

        # Write header
        output_file.write(header)
        output_file.write(struct.pack(">I", header_crc))

        # Write each fork
        for fork_data in (data_fork, rsrc_fork):
            output_file.write(fork_data)

            # Align to 128 bytes
            pad = len(fork_data) % 128
            if pad != 0:
                output_file.write(b'\x00' * (128 - pad))
