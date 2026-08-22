"""تحويل أصول Mini App الكبيرة إلى WebP بأبعاد مناسبة لواجهة Telegram."""

from pathlib import Path

from PIL import Image

ASSETS = {
    "mihrab-hero": {"max_width": 1280, "quality": 82},
    "mihrab-mark": {"max_width": 384, "quality": 86},
    "prayer-card-texture": {"max_width": 512, "quality": 68},
}


def main() -> None:
    assets_dir = Path(__file__).parents[1] / "miniapp" / "client" / "public" / "assets"
    for stem, options in ASSETS.items():
        source = assets_dir / f"{stem}.png"
        target = assets_dir / f"{stem}.webp"
        with Image.open(source) as image:
            width, height = image.size
            target_width = min(width, options["max_width"])
            target_height = round(height * target_width / width)
            if (width, height) != (target_width, target_height):
                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            image.save(target, "WEBP", quality=options["quality"], method=6)
        print(f"{source.name} -> {target.name}: {target_width}x{target_height}")


if __name__ == "__main__":
    main()
