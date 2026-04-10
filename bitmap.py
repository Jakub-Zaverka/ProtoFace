import argparse

from PIL import Image


def convert_image(input_path, output_path, width, height, threshold=128, invert=False):
    """
    Nacte obrazek, zmeni velikost, prevede ho na cernobilou bitmapu a ulozi.
    """
    image = Image.open(input_path).convert("L")
    image = image.resize((width, height), Image.Resampling.LANCZOS)

    # Prevod na 1bit obraz podle zvoleneho prahu.
    image = image.point(lambda pixel: 255 if pixel >= threshold else 0, mode="1")

    if invert:
        image = image.point(lambda pixel: 0 if pixel else 255, mode="1")

    image.save(output_path)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prevod obrazku na bitmapu s danou velikosti."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Vstupni obrazek, napriklad 1.jpg",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Vystupni obrazek, napriklad face.bmp",
    )
    parser.add_argument(
        "--width",
        required=True,
        type=int,
        help="Cilova sirka obrazku",
    )
    parser.add_argument(
        "--height",
        required=True,
        type=int,
        help="Cilova vyska obrazku",
    )
    parser.add_argument(
        "--threshold",
        default=128,
        type=int,
        help="Prah pro prevod na cernobilou bitmapu, vychozi je 128",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Prohodi cernou a bilou",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert_image(
        input_path=args.input,
        output_path=args.output,
        width=args.width,
        height=args.height,
        threshold=args.threshold,
        invert=args.invert,
    )
    print("Ulozeno do:", args.output)
