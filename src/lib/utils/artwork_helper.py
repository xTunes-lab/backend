import base64
from io import BytesIO
from mutagen.mp4 import MP4Cover
import requests


class ArtworkHelper:
    @staticmethod
    def mp4_cover_to_bytes(covers: list[MP4Cover]) -> list[bytes]:
        bytes_cover = []
        for cover in covers:
            bytes_cover.append(bytes(cover))
        return bytes_cover

    @staticmethod
    def mp4cover_to_b64str(covers: list[MP4Cover]) -> list[str]:
        value = []
        for cover in covers:
            if isinstance(cover, MP4Cover):
                value.append(ArtworkHelper.image_bytes_to_base64(cover))
            elif isinstance(cover, str):
                value.append(cover)
        return value

    @staticmethod
    def image_bytes_to_base64(cover: MP4Cover):
        if type(cover) is not MP4Cover:
            raise Exception("the cover is not MP4cover format")

        if cover.imageformat == MP4Cover.FORMAT_JPEG:
            prefix = "data:image/jpeg;base64,"
        elif cover.imageformat == MP4Cover.FORMAT_PNG:
            prefix = "data:image/png;base64,"
        else:
            raise Exception("unsupported image format")
        bstr = base64.b64encode(bytes(cover)).decode("utf-8")
        b64str = prefix + bstr
        return b64str

    @staticmethod
    def artwork_to_base64(url) -> str:
        r2 = requests.get(url)
        r2.raise_for_status()
        img_data = f"data:{r2.headers['Content-Type']};base64,{base64.b64encode(r2.content).decode("utf-8")}"
        return img_data

    @staticmethod
    def get_b64_image_type(img_b64: str) -> str | None:
        mime = img_b64.split(";")[0].split(":")[1]  # "image/png"
        ext = mime.split("/")[1]                # "png"
        if "data:image/jpeg;base64," in img_b64:
            return MP4Cover.FORMAT_JPEG
        elif "data:image/png;base64," in img_b64:
            return MP4Cover.FORMAT_PNG
        else:
            raise Exception("not valid image type")

    @staticmethod
    def resize_artwork(img_b64: str, size=(400, 400)):
        from PIL import Image
        prefix, data = img_b64.split(",")
        data_bytes = base64.b64decode(data)
        img = Image.open(BytesIO(data_bytes))
        resized = img.copy()
        resized.thumbnail(size)
        resized_bytes = BytesIO()
        img_type = ArtworkHelper.get_b64_image_type(img_b64)
        if img_type == 13:
            resized.save(resized_bytes, format="jpeg")
        else:
            resized.save(resized_bytes, format="png")
        result = prefix + "," + \
            base64.b64encode(resized_bytes.getvalue()).decode("utf-8")
        resized_bytes.close()
        return result

    @staticmethod
    def b64_to_cover(img: str) -> MP4Cover:
        img_type = ArtworkHelper.get_b64_image_type(img)
        _, data = img.split(",")
        img_bytes = base64.b64decode(data)
        cover = MP4Cover(img_bytes, img_type)
        return cover
