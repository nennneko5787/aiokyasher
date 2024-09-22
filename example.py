import asyncio

from aiokyasher import Kyash


async def main():
    kyash = Kyash()
    await kyash.login(
        "メールアドレス", "パスワード", proxy=None
    )  # 引数にプロキシを設定できる、proxy=dict
    otp = input("OTP? :")  # SMSに届いた6桁の認証番号
    await kyash.validate_otp(otp)
    print(kyash.access_token)  # 有効期限は1ヶ月
    print(kyash.client_uuid)
    print(
        kyash.installation_uuid
    )  # クライアントUUIDとインストレーションUUIDは2つで1セット

    await kyash.login(
        "メールアドレス",
        "パスワード",
        "登録済みクライアントUUID",
        "登録済みインストレーションUUID",
    )  # これでログイン時のOTP認証をスキップできる
    await kyash.login(access_token="アクセストークン")  # またはトークンでログイン

    await kyash.get_profile()  # プロフィール取得
    print(kyash.username)  # ユーザーネーム
    print(kyash.icon)  # アイコン
    print(kyash.myouzi)  # 苗字
    print(kyash.namae)  # 名前
    print(kyash.phone)  # 電話番号
    print(kyash.is_kyc)  # 本人確認されているかどうか、True or False

    await kyash.get_wallet()  # 残高照会
    print(kyash.wallet_uuid)  # おさいふUUID
    print(kyash.all_balance)  # 合計残高
    print(kyash.money)  # 出金可能なキャッシュマネー
    print(kyash.value)  # 出金不可のキャッシュバリュー
    print(kyash.point)  # ポイント

    await kyash.get_history(
        wallet_uuid=kyash.wallet_uuid, limit=3
    )  # 支出入の履歴を取得する、wallet_uuidを入力しなかったらその場で取得するので入力しなくてもOK
    print(kyash.timelines)  # リスト型、支出入履歴

    await kyash.get_summary(
        year=2024, month=6
    )  # 支出入のカテゴリーを取得する、何も入力しないと今日の西暦と月になる
    print(kyash.summary)  # ↑で取得したレポート


asyncio.run(main())
