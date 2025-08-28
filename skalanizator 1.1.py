import logging
import os
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class SkalanizatorMod(loader.Module):
    """Скаланизатор — добавляет текст на картинки"""

    strings = {"name": "Скаланизатор"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            "FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "Путь до шрифта"
        )
        self.images = []

    async def client_ready(self, client, db):
        # Ничего не пишем в чат при загрузке
        pass

    async def jhelpcmd(self, message):
        """Показать меню Скаланизатора"""
        text = (
            "🪐 Скаланизатор v1.1 (✿◠‿◠)\n"
            "▫️ .j [номер (опц.)] [текст/реплай] — создать мем\n"
            "▫️ .jadd <ссылка> — добавить картинку\n"
            "▫️ .jclear — очистить список картинок\n"
            "▫️ .jdel <номер/диапазон> — удалить картинку\n"
            "▫️ .jlist — список картинок\n"
        )
        await utils.answer(message, text)

    def _add_text(self, img_path, text):
        img = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(self.config["FONT_PATH"], size=40)
        except Exception:
            font = ImageFont.load_default()

        # Разбивка длинного текста на строки
        max_width = img.width - 40
        lines = []
        for line in text.split("\n"):
            wrapped = textwrap.wrap(line, width=40)
            lines.extend(wrapped if wrapped else [""])

        # Высота всего блока текста
        line_height = font.getbbox("A")[3] - font.getbbox("A")[1] + 5
        total_height = line_height * len(lines)

        y = img.height - total_height - 20
        for line in lines:
            w = font.getlength(line)
            x = (img.width - w) / 2
            draw.text((x, y), line, font=font, fill="white", stroke_width=2, stroke_fill="black")
            y += line_height

        out_path = "/tmp/out.jpg"
        img.save(out_path, "JPEG")
        return out_path

    async def jcmd(self, message):
        """[номер (опц.)] [текст/реплай] — создать мем"""
        args = utils.get_args_raw(message).split(maxsplit=1)

        if args and args[0].isdigit():
            idx = int(args[0]) - 1
            text = args[1] if len(args) > 1 else ""
        else:
            idx = 0
            text = args[0] if args else ""

        reply = await message.get_reply_message()
        if reply and not text:
            text = reply.raw_text or ""

        if not self.images:
            await utils.answer(message, "🚫 Список картинок пуст. Добавь их через .jadd <ссылка>")
            return

        if idx < 0 or idx >= len(self.images):
            await utils.answer(message, "🚫 Неверный номер картинки")
            return

        img_path = self._download_image(self.images[idx])
        out_path = self._add_text(img_path, text or "")
        await message.respond(file=out_path, reply_to=reply.id if reply else None)
        await message.delete()

    async def jaddcmd(self, message):
        """<ссылка> — добавить картинку"""
        url = utils.get_args_raw(message)
        if not url:
            await utils.answer(message, "🚫 Укажи ссылку на картинку")
            return
        self.images.append(url)
        await utils.answer(message, f"✅ Картинка добавлена под номером {len(self.images)}")

    async def jlistcmd(self, message):
        """Список картинок"""
        if not self.images:
            await utils.answer(message, "🚫 Список пуст")
            return
        out = "📂 Список картинок:\n\n"
        for i, url in enumerate(self.images, start=1):
            out += f"{i}. {url}\n"
        await utils.answer(message, out)

    async def jclearcmd(self, message):
        """Очистить список картинок"""
        self.images.clear()
        await utils.answer(message, "🗑 Список картинок очищен")

    async def jdelcmd(self, message):
        """<номер/диапазон> — удалить картинку"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "🚫 Укажи номер или диапазон для удаления")
            return

        try:
            if "-" in args:
                start, end = map(int, args.split("-"))
                del self.images[start - 1:end]
                await utils.answer(message, f"🗑 Удалены картинки с {start} по {end}")
            else:
                idx = int(args) - 1
                url = self.images.pop(idx)
                await utils.answer(message, f"🗑 Картинка удалена: {url}")
        except Exception:
            await utils.answer(message, "🚫 Ошибка удаления. Проверь номер.")

    def _download_image(self, url):
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            raise Exception("Ошибка загрузки картинки")
        img_path = "/tmp/input.jpg"
        with open(img_path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        return img_path