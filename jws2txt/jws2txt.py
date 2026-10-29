import argparse
import os
from .helpers.helpers import JWSFile


def str2bool(v: str) -> bool:
    """Converts string to bool."""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def parse_metadata_mode(v: str) -> str:
    """Parses and normalizes metadata output mode (case-insensitive)."""
    s = str(v).strip().lower()
    if s in ('none', 'false', 'f', 'no', '0'):
        return 'none'
    elif s in ('header', 'head'):
        return 'header'
    elif s in ('json', 'sidecar'):
        return 'json'
    elif s in ('both', 'all', 'true', 't', 'yes', '1'):
        return 'both'
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid metadata mode: {v!r}. Choose from 'none', 'header', 'json', or 'both'."
        )

def main():
    
    parser = argparse.ArgumentParser(description='Converts *.jws or *jwb files to human\
                                     -readable text files.')
    parser.add_argument('--in-path', type=str, required=True,
                        help="Path to file or folder containing files for conversion.")
    parser.add_argument('--out-dir', type=str,  help='Output folder')
    parser.add_argument('--delimiter', type=str, default='\t', help='Delimiter used in\
                         saved text files.')
    parser.add_argument('--comments', type=str2bool, choices=[True, False], default=True,  # noqa: E501
                         help='Write sample information.')
    parser.add_argument('--header', type=str2bool, choices=[True, False], default=True,
                         help='Write column headers.')
    parser.add_argument('--metadata', type=parse_metadata_mode, default='none', metavar='MODE',
                         help="Metadata export: 'none' (default), 'header' (top comment lines in text file), 'json' (sidecar file), or 'both'.")

    args = parser.parse_args()

    if not os.path.exists(args.in_path):
        raise FileNotFoundError(f"{args.in_path} does not exist.")

    if os.path.isfile(args.in_path):
        out_dir = args.out_dir if args.out_dir else os.path.dirname(args.in_path)
        if not out_dir:
            out_dir = "."
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        out_file_path = os.path.join(
            out_dir, os.path.splitext(os.path.basename(args.in_path))[0] + ".txt"
        )
        JWSFile(path=args.in_path).write_data(
            out_file=out_file_path,
            delimiter=args.delimiter,
            write_comments=args.comments,
            write_header=args.header,
            metadata=args.metadata,
        )
        return

    if args.out_dir is None:
        args.out_dir = args.in_path

    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir, exist_ok=True)

    for (root, dirs, files) in os.walk(args.in_path, topdown=True):
        gen = (file for file in files if file.endswith(('.jwb', '.jws')))

        for file in gen:

            out_file_path = os.path.join(args.out_dir, ''.join((os.path.splitext(file)[0],  # noqa: E501
                                                                 '.txt')))
            jws_file_path = os.path.join(root, file)

            JWSFile(path=jws_file_path).write_data(out_file=out_file_path,
                                                   delimiter=args.delimiter,
                                                   write_comments=args.comments,
                                                   write_header=args.header,
                                                   metadata=args.metadata)
      

if __name__ == '__main__':
    main()
