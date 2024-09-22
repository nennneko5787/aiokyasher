import datetime
from uuid import uuid4

from bs4 import BeautifulSoup
from httpx import AsyncClient


class KyashError(Exception):
    pass


class KyashLoginError(Exception):
    pass


class NetWorkError(Exception):
    pass


class Kyash:
    """
        スマホアプリ「Kyash」をPythonから操作するモジュール
        SMS以外は必要ありません。
    """

    def __init__(self, proxy: dict = None):
        """Kyasherを呼び出します。

        Args:
            proxy (dict, optional): 内部のHTTPライブラリ(HTTPX)で使われるプロキシ。
        """
        self.http = AsyncClient(proxies=proxy)

    async def login(
        self,
        email: str = None,
        password: str = None,
        client_uuid: str = None,
        installation_uuid: str = None,
        access_token: str = None,
    ):
        """Kyashにログインします。
           クライアントUUIDとインストレーションUUIDのペアがある場合や、アクセストークンがある場合は、OTPをスキップできます。
           それ以外の場合は、login()の実行後、validate_otp()を実行してください。

        Args:
            email (str, optional): Kyashでログインするために使うメールアドレス。
            password (str, optional): Kyashでログインするために使うパスワード。
            client_uuid (str, optional): OTPをスキップするために使うクライアントUUID。
            installation_uuid (str, optional): OTPをスキップするために使うインストレーションUUID。
            access_token (str, optional): Kyashのアクセストークン。

        Raises:
            KyashLoginError: 電話番号 & パスワードを入力するか、アクセストークンを入力してください
            NetWorkError: ネットワークエラー。
            KyashLoginError: Kyashから発行されるエラー。
            KyashLoginError: 登録されていないUUID
        """

        if email == password == access_token:
            raise KyashLoginError(
                "電話番号 & パスワードを入力するか、アクセストークンを入力してください"
            )

        self.email = email
        self.password = password
        self.access_token = access_token

        if client_uuid:
            self.client_uuid = client_uuid
        else:
            self.client_uuid = str(uuid4()).upper()

        if installation_uuid:
            self.installation_uuid = installation_uuid
        else:
            self.installation_uuid = str(uuid4()).upper()

        try:
            iosstore = await self.http.get(
                "https://apps.apple.com/jp/app/kyash-%E3%82%AD%E3%83%A3%E3%83%83%E3%82%B7%E3%83%A5-%E3%83%81%E3%83%A3%E3%83%BC%E3%82%B8%E5%BC%8Fvisa%E3%82%AB%E3%83%BC%E3%83%89/id1084264883",
            )
        except Exception as e:
            raise NetWorkError(e)

        self.version = (
            BeautifulSoup(iosstore.text, "html.parser")
            .find(class_="l-column small-6 medium-12 whats-new__latest__version")
            .text.split()[1]
        )
        self.headers = {
            "Host": "api.kyash.me",
            "Content-Type": "application/json",
            "X-Kyash-Client-Id": self.client_uuid,
            "Accept": "application/json",
            "X-Kyash-Device-Language": "ja",
            "X-Kyash-Client-Version": self.version,
            "X-Kyash-Device-Info": "iPhone 8, Version:16.7.5",
            "Accept-Language": "ja-jp",
            "X-Kyash-Date": str(
                round(
                    datetime.datetime.now(
                        datetime.timezone(datetime.timedelta(hours=9))
                    ).timestamp()
                )
            ),
            "Accept-Encoding": "gzip, deflate, br",
            # "X-Kyash-Device-Uptime-Mills": 540266465,
            "User-Agent": "Kyash/2 CFNetwork/1240.0.4 Darwin/20.6.0",
            "X-Kyash-Installation-Id": self.installation_uuid,
            "X-Kyash-Os": "iOS",
            "Connection": "keep-alive",
        }
        if access_token:
            self.headers["X-Auth"] = access_token
        else:
            payload = {"email": email, "password": password}
            login = (
                await self.http.post(
                    "https://api.kyash.me/v2/login",
                    headers=self.headers,
                    json=payload,
                )
            ).json()
            if login["code"] != 200:
                raise KyashLoginError(login["error"]["message"])

            if client_uuid and installation_uuid:
                if not login["result"]["data"]["token"]:
                    raise KyashLoginError("登録されていないUUID")

                self.access_token = login["result"]["data"]["token"]  # 1ヶ月もつよ
                self.refresh_token = login["result"]["data"]["refreshToken"]
                self.headers["X-Auth"] = self.access_token

    async def validate_otp(self, otp: str) -> dict:
        """Kyashから発行されるOTPコードを使用してログインします。

        Args:
            otp (str): Kyashから発行されるKyashコード。

        Raises:
            KyashLoginError: Kyashから発行されるエラー。

        Returns:
            dict: レスポンス。
        """
        payload = {"verificationCode": otp, "email": self.email}
        get_token = (
            await self.http.post(
                "https://api.kyash.me/v2/login/mobile/verify",
                headers=self.headers,
                json=payload,
            )
        ).json()
        if get_token["code"] != 200:
            raise KyashLoginError(get_token["error"]["message"])

        self.access_token = get_token["result"]["data"]["token"]  # 1ヶ月もつよ
        self.refresh_token = get_token["result"]["data"]["refreshToken"]
        self.headers["X-Auth"] = get_token["result"]["data"]["token"]

        return get_token

    async def get_profile(self) -> dict:
        """Kyashのプロファイルを取得します。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: Kyashのプロファイル。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        getprofile = (
            await self.http.get("https://api.kyash.me/v1/me", headers=self.headers)
        ).json()
        if getprofile["code"] != 200:
            raise KyashError(getprofile["error"]["message"])

        self.username = getprofile["result"]["data"]["userName"]
        self.icon = getprofile["result"]["data"]["imageUrl"]
        self.myouzi = getprofile["result"]["data"]["lastNameReal"]
        self.namae = getprofile["result"]["data"]["firstNameReal"]
        self.phone = getprofile["result"]["data"]["phoneNumber"]
        self.is_kyc = getprofile["result"]["data"]["kyc"]

        return getprofile

    async def get_wallet(self) -> dict:
        """Kyashポイント、Kyashバリュー、及びKyashマネーを取得します。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: Kyashのウォレット情報。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        getwallet = (
            await self.http.get(
                "https://api.kyash.me/v1/me/primary_wallet",
                headers=self.headers,
            )
        ).json()
        if getwallet["code"] != 200:
            raise KyashError(getwallet["error"]["message"])

        self.wallet_uuid = getwallet["result"]["data"]["uuid"]
        self.all_balance = getwallet["result"]["data"]["balance"]["amount"]
        self.money = getwallet["result"]["data"]["balance"]["amountBreakdown"][
            "kyashMoney"
        ]
        self.value = getwallet["result"]["data"]["balance"]["amountBreakdown"][
            "kyashValue"
        ]
        self.point = getwallet["result"]["data"]["pointBalance"]["availableAmount"]

        return getwallet

    async def get_history(self, wallet_uuid: str = None, limit: int = 3) -> dict:
        """ウォレットの使用履歴を確認します。

        Args:
            wallet_uuid (str, optional): ウォレットUUID。
            limit (int, optional): 取得する履歴の数。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: ウォレットUUIDを取得する際にKyashから発行されるエラー。
            KyashError: 履歴を取得する際にKyashから発行されるエラー。

        Returns:
            dict: ウォレットの使用履歴。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        param = {"limit": limit}
        if not wallet_uuid:
            getwallet = (
                await self.http.get(
                    "https://api.kyash.me/v1/me/primary_wallet",
                    headers=self.headers,
                )
            ).json()
            if getwallet["code"] != 200:
                raise KyashError(getwallet["error"]["message"])
            wallet_uuid = getwallet["result"]["data"]["uuid"]

        gethistory = (
            await self.http.get(
                f"https://api.kyash.me/v1/me/wallets/{wallet_uuid}/timeline",
                headers=self.headers,
                params=param,
            )
        ).json()
        if gethistory["code"] != 200:
            raise KyashError(gethistory["error"]["message"])

        self.timelines = gethistory["result"]["data"]["timelines"]

        return gethistory

    async def get_summary(self, year: int = None, month: int = None) -> dict:
        """家計簿を取得します。

        Args:
            year (int, optional): 年。
            month (int, optional): 月。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: 家計簿。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        if not year:
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            year = now.year
        if not month:
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            month = now.month

        if int(month) < 10:
            month = f"0{month}"

        getsummary = (
            await self.http.get(
                f"https://api.kyash.me/v1/monthly_timeline/summary/{year}-{month}",
                headers=self.headers,
            )
        ).json()
        if getsummary["code"] != 200:
            raise KyashError(getsummary["error"]["message"])

        self.summary = getsummary["result"]["data"]["summary"]

        return getsummary

    async def create_link(
        self, amount: int, message: str = "", is_claim: bool = False
    ) -> dict:
        """送金・請求リンクを作成します。

        Args:
            amount (int): 請求額。
            message (str, optional): 送金・請求するときに表示されるメッセージ。
            is_claim (bool, optional): リンクを請求リンクとして生成するかどうか。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: 作成されたリンクとその情報。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        payload = {
            "uuidClient": str(uuid4()).upper(),
            "amount": amount,
            "repeatable": False,
            "action": 1,
            "message": {"text": message, "uuidClient": str(uuid4()).upper()},
            "service": "share",
        }
        if is_claim:
            payload["action"] = 2
            payload["repeatable"] = True

        create = (
            await self.http.post(
                "https://api.kyash.me/v1/me/links",
                headers=self.headers,
                json=payload,
            )
        ).json()
        if create["code"] != 200:
            raise KyashError(create["error"]["message"])

        self.created_link = create["result"]["data"]["link"]

        return create

    async def link_check(self, url: str) -> dict:
        """送金・請求リンクが有効なものかを確認します。

        Args:
            url (str): https://kyash.me/payments/から始まるリンク、またはリンクID。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: Kyashから発行されるエラー。
            KyashError: 処理済みのリンクのため、チェックに失敗しました

        Returns:
            dict: リンクの情報。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        if not "https://kyash.me/payments/" in url:
            url = "https://kyash.me/payments/" + url

        try:
            link_info = await self.http.get(url).text
            soup = BeautifulSoup(link_info, "html.parser")
            try:
                self.link_amount = soup.find(
                    class_="amountText text_send"
                ).text.replace("¥", "")
                self.link_uuid = (
                    soup.find(class_="btn_send")
                    .get("data-href-app")
                    .replace("kyash://claim/", "")
                )
                self.send_to_me = True
            except:
                self.link_amount = soup.find(
                    class_="amountText text_request"
                ).text.replace("¥", "")
                self.link_uuid = (
                    soup.find(class_="btn_request")
                    .get("data-href-app")
                    .replace("kyash://request/u/", "")
                )
                self.send_to_me = False

            link_info = (
                await self.http.get(
                    f"https://api.kyash.me/v1/links/{self.link_uuid}",
                    headers=self.headers,
                )
            ).json()
            if link_info["code"] != 200:
                raise KyashError(link_info["error"]["message"])
            self.link_public_id = link_info["result"]["data"]["target"]["publicId"]
            self.link_sender_name = link_info["result"]["data"]["target"]["userName"]
        except:
            raise KyashError("処理済みのリンクのため、チェックに失敗しました")

        return link_info

    async def link_recieve(self, url: str = None, link_uuid: str = None) -> dict:
        """送金リンクを受理します。

        Args:
            url (str, optional): https://kyash.me/payments/から始まるリンク、またはリンクID。
            link_uuid (str, optional): リンクUUID。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: 有効な受け取りリンクがありません
            KyashError: 処理済みまたは受け取りリンクではありません
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: 使用されたリンクの情報。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        if not link_uuid:
            if not url:
                raise KyashError("有効な受け取りリンクがありません")

            if not "https://kyash.me/payments/" in url:
                url = "https://kyash.me/payments/" + url

            try:
                link_info = await self.http.get(url)
                soup = BeautifulSoup(link_info.text, "html.parser")
                # link_amount=soup.find(class_="amountText text_send").text.replace("¥","")
                link_uuid = (
                    soup.find(class_="btn_send")
                    .get("data-href-app")
                    .replace("kyash://claim/", "")
                )
            except:
                raise KyashError("処理済みまたは受け取りリンクではありません")

        recieve = (
            await self.http.put(
                f"https://api.kyash.me/v1/links/{link_uuid}/receive",
                headers=self.headers,
            )
        ).json()
        if recieve["code"] != 200:
            raise KyashError(recieve["error"]["message"])

        return recieve

    async def link_cancel(self, url: str = None, link_uuid: str = None) -> dict:
        """送金・請求リンクを削除します。

        Args:
            url (str, optional): https://kyash.me/payments/から始まるリンク、またはリンクID。
            link_uuid (str, optional): リンクUUID。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: 有効な受け取りリンクがありません
            KyashError: Kyashから発行されるエラー。

        Returns:
            dict: 削除されたリンクの情報。
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        if not link_uuid:
            if not url:
                raise KyashError("有効な受け取りリンクがありません")

            if not "https://kyash.me/payments/" in url:
                url = "https://kyash.me/payments/" + url

            link_info = await self.http.get(url)
            soup = BeautifulSoup(link_info.text, "html.parser")
            # link_amount=soup.find(class_="amountText text_send").text.replace("¥","")
            link_uuid = (
                soup.find(class_="btn_send")
                .get("data-href-app")
                .replace("kyash://claim/", "")
            )

        cancel = (
            await self.http.delete(
                f"https://api.kyash.me/v1/links/{link_uuid}",
                headers=self.headers,
            )
        ).json()
        if cancel["code"] != 200:
            raise KyashError(cancel["error"]["message"])

        return cancel

    async def send_to_link(
        self, url: str = None, message: str = "", link_info: str = None
    ):
        """請求リンクを受理します。

        Args:
            url (str, optional): https://kyash.me/payments/から始まるリンク、またはリンクID。
            message (str, optional): 請求リンクを受理するときに表示されるメッセージ。
            link_uuid (str, optional): リンクUUID。

        Raises:
            KyashLoginError: まずはログインしてください
            KyashError: 有効な受け取りリンクがありません
            KyashError: リンクの情報を取得する際にKyashから発行されるエラー。
            KyashError: 処理済みまたは請求リンクではありません
            KyashError: 請求リンクを受理するときにKyashから発行されるエラー。

        Returns:
            _type_: _description_
        """
        if not self.access_token:
            raise KyashLoginError("まずはログインしてください")

        if not link_info:
            if not url:
                raise KyashError("有効な受け取りリンクがありません")

            if not "https://kyash.me/payments/" in url:
                url = "https://kyash.me/payments/" + url

            try:
                link_info = await self.http.get(url).text
                soup = BeautifulSoup(link_info, "html.parser")
                link_amount = soup.find(class_="amountText text_request").text.replace(
                    "¥", ""
                )
                link_uuid = (
                    soup.find(class_="btn_request")
                    .get("data-href-app")
                    .replace("kyash://request/u/", "")
                )
                link_info = (
                    await self.http.get(
                        f"https://api.kyash.me/v1/links/{link_uuid}",
                        headers=self.headers,
                    )
                ).json()
                if link_info["code"] != 200:
                    raise KyashError(link_info["error"]["message"])
                print(link_info)
                link_public_id = link_info["result"]["data"]["target"]["publicId"]
                link_sender_name = link_info["result"]["data"]["target"]["userName"]
            except:
                raise KyashError("処理済みまたは請求リンクではありません")

        payload = {
            "transactionMessage": {"text": message, "uuidClient": str(uuid4()).upper()},
            "amount": int(link_amount),
            "publicId_to": link_public_id,
            "action": 1,
            "username_to": link_sender_name,
            "currency": "JPY",
        }

        send = (
            await self.http.put(
                f"https://api.kyash.me/v1/links/{link_uuid}",
                headers=self.headers,
                json=payload,
            )
        ).json()

        if send["code"] != 200:
            raise KyashError(send["error"]["message"])

        return send
