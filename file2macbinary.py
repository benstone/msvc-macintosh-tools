import pathlib
import argparse
import logging

import macbinary

logger = logging.getLogger("file2macbinary")


def main():
    parser = argparse.ArgumentParser(description="Pack a file using the MacBinary format")
    parser.add_argument("output_file", help="MacBinary file to write")
    parser.add_argument("--data", help="File containing data fork")
    parser.add_argument("--rsrc", help="File containing resource fork")
    parser.add_argument("--creator", help="File creator", default="TEST")
    parser.add_argument("--type", help="File type", default="TEST")
    parser.add_argument("--name", help="File name")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    data_fork = b''
    rsrc_fork = b''

    if args.data is not None:
        data_fork = open(args.data, "rb").read()
    if args.rsrc is not None:
        rsrc_fork = open(args.rsrc, "rb").read()

    output_file_path = pathlib.Path(args.output_file)
    if args.name is not None:
        file_name = args.name
    else:
        file_name = output_file_path.name

    macbinary_file = macbinary.MacBinaryIIFile(
        data_fork=data_fork,
        resource_fork=rsrc_fork,
        file_name=file_name,
        file_creator=args.creator,
        file_type=args.type,
    )

    with open(output_file_path, "wb") as output_file:
        macbinary_file.write(output_file)


if __name__ == "__main__":
    main()
