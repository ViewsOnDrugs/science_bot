import subprocess
from scibot.telebot import telegram_bot_sendtext


def main():
    ps = subprocess.Popen(("ps", "aux"), stdout=subprocess.PIPE)
    out_std = subprocess.check_output(("grep", "scibot"), stdin=ps.stdout)
    out_std = out_std.decode("utf-8")
    ps.wait()
    telegram_bot_sendtext(f"{out_std}")


if __name__ == "__main__":
    main()
