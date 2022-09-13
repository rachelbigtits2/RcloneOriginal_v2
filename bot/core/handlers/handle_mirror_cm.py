from time import time
from requests import get
from bot import LOGGER
from bot.core.get_vars import get_val
from bot.core.set_vars import set_val
from bot.downloaders.mirror_download import handle_mirror_download
from bot.utils.bot_utils import get_content_type, is_gdrive_link, is_magnet, is_mega_link, is_url
from re import match as re_match
from bot.utils.direct_link_generator import direct_link_generator
from bot.utils.exceptions import DirectDownloadLinkException
from bot.utils.get_size_p import get_readable_size
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def handle_mirror_command(client, message):
    await mirror(client, message)

async def handle_zip_mirror_command(client, message):
    await mirror(client, message, isZip=True)

async def handle_unzip_mirror_command(client, message):
    await mirror(client, message, extract=True)

async def handle_qbit_mirror_command(client, message):
    await mirror(client, message, isQbit=True)

async def mirror(client, message, isZip=False, extract=False, isQbit=False):
    user_id= message.from_user.id
    chat_id = message.chat.id
    if user_id in get_val("ALLOWED_USERS") or chat_id in get_val("ALLOWED_CHATS") or user_id == get_val("OWNER_ID"):
        replied_message= message.reply_to_message
        if replied_message is not None :
            mesg = message.text
            pswdMsg = mesg.split(' pswd: ')
            if len(pswdMsg) > 1:
                pswd = pswdMsg[1]
                print("Password: {}".format(pswd))
            else:
                pswd= None  
            file= None
            media_array = [replied_message.document, replied_message.video, replied_message.audio]
            for i in media_array:
                if i is not None:
                    file = i
            tag = f"@{replied_message.from_user.username}"
            if file is not None:
                if not isQbit: 
                    if file.mime_type != "application/x-bittorrent":
                        name= file.file_name
                        size= get_readable_size(file.file_size)
                        msg = f"<b>Which name do you want to use?</b>\n\n<b>Name</b>: `{name}`\n\n<b>Size</b>: `{size}`"
                        set_val("FILE", file)
                        set_val("IS_ZIP", isZip)
                        set_val("EXTRACT", extract)
                        set_val("PSWD", pswd)
                        keyboard = [[InlineKeyboardButton(f"📄 By default", callback_data= f'mirrormenu_default'),
                                InlineKeyboardButton(f"📝 Rename", callback_data='mirrormenu_rename')],
                                [InlineKeyboardButton("Close", callback_data= f"mirrorsetmenu^selfdest")]]
                        return await message.reply_text(msg, quote= True, reply_markup= InlineKeyboardMarkup(keyboard))
                    else:
                        return await message.reply_text("Use qbmirror command to mirror torrent file")   
                else:
                    path = await client.download_media(file)
                    file_name = str(time()).replace(".", "") + ".torrent"
                    with open(path, "rb") as f:
                        with open(file_name, "wb") as t:
                            t.write(f.read())
                    link = str(file_name)
                    await handle_mirror_download(client, message, None, tag, pswd, link, isZip, extract, isQbit)
            else:
                reply_text = replied_message.text     
                if is_url(reply_text) or is_magnet(reply_text): 
                    link = reply_text.strip()
                    if isQbit:
                        if not is_magnet(link):
                            if link.endswith('.torrent'):
                                content_type = None
                            else:
                                content_type = get_content_type(link)
                            if content_type is None or re_match(r'application/x-bittorrent|application/octet-stream', content_type):
                                try:
                                    resp = get(link, timeout=10, headers = {'user-agent': 'Wget/1.12'})
                                    LOGGER.info(resp)
                                    if resp.status_code == 200:
                                        LOGGER.info(resp.status_code)
                                        file_name = str(time()).replace(".", "") + ".torrent"
                                        LOGGER.info(file_name)
                                        with open(file_name, "wb") as t:
                                            t.write(resp.content)
                                        link = str(file_name)
                                        LOGGER.info(link)
                                    else:
                                        return await message.reply_text(f"{tag} ERROR: link got HTTP response: {resp.status_code}")     
                                except Exception as e:
                                    error = str(e).replace('<', ' ').replace('>', ' ')
                                    if error.startswith('No connection adapters were found for'):
                                        link = error.split("'")[1]
                                    else:
                                        LOGGER.error(str(e))
                                        return await message.reply_text(tag + " " + error) 
                    else:
                        if is_magnet(link) or link.endswith('.torrent'):
                            return await message.reply_text("Use qbmirror command to mirror torrent or magnet link")
                        if is_gdrive_link(link):
                            return await message.reply_text("Not currently supported Google Drive links") 
                        if not is_mega_link(link) and not is_magnet(link) and not is_gdrive_link(link) \
                            and not link.endswith('.torrent'):
                            content_type = get_content_type(link)
                            if content_type is None or re_match(r'text/html|text/plain', content_type):
                                try:
                                    link = direct_link_generator(link)
                                    LOGGER.info(f"Generated link: {link}")
                                except DirectDownloadLinkException as e:
                                    if str(e).startswith('ERROR:'):
                                        return await message.reply_text(str(e))
                await handle_mirror_download(client, message, file, tag, pswd, link, isZip, extract, isQbit)
        else:
            if isZip or extract:
                await message.reply_text("<b>Reply to a Telegram file</b>\n\n<b>For password use this format:</b>\n/zipmirror pswd: password", quote=True) 
            elif isQbit:
                await message.reply_text("<b>Reply to a torrent or magnet link</b>", quote=True)
            else:
                await message.reply_text("<b>Reply to a link or Telegram file</b>\n", quote=True) 
    else:
        await message.reply('Not Authorized user', quote=True)


    