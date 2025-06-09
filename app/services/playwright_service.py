import time
import os
from playwright.sync_api import sync_playwright, expect
import re

class PlaywrightService:
    """
    一個使用 Playwright 來執行網頁自動化任務的服務。
    """
    def run_seagm_automation(self,
                             seagm_username: str,
                             seagm_password: str,
                             game_name: str,
                             player_id: str,
                             player_server: str,
                             product_id: str):
        """
        執行 SEAGM 網站的自動化儲值流程。
        - seagm_username: 用於登入的SEAGM帳號
        - seagm_password: 用於登入的SEAGM密碼
        - game_name: 要搜尋的遊戲名稱 (用於導航)
        - player_id: 玩家的遊戲內ID
        - player_server: 玩家的遊戲伺服器 (e.g., "Asia")
        - product_id: 要購買的商品ID (e.g., "13667")
        """
        auth_file = "auth_state.json"

        with sync_playwright() as p:
            # 在雲端環境 (如 Zeabur) 執行時，必須設定為 headless=True
            browser = p.chromium.launch(headless=True)

            # 檢查是否存在已儲存的登入狀態
            context = browser.new_context(storage_state=auth_file if os.path.exists(auth_file) else None)
            page = context.new_page()

            try:
                print("正在檢查登入狀態並導航至 SEAGM 網站...")
                page.goto("https://www.seagm.com/zh-tw", wait_until="load", timeout=60000)

                # 透過檢查登入按鈕是否存在，來判斷是否需要登入
                if page.locator("#login-btn").is_visible():
                    print("未找到有效登入狀態，將執行完整登入流程...")

                    # 步驟 1: 處理 Cookie 同意按鈕
                    try:
                        cookie_button = page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                        expect(cookie_button).to_be_visible(timeout=15000)
                        cookie_button.click()
                        page.wait_for_timeout(300)
                    except Exception as e:
                        print(f"找不到或無法點擊 Cookie 按鈕: {e}")

                    # 步驟 2: 點擊語言/貨幣切換器並選擇馬來西亞
                    page.locator("div.language_currency").click()
                    page.wait_for_timeout(300)
                    page.locator('div.region_item[region="my"]').click()
                    page.wait_for_timeout(300)

                    # 步驟 3: 執行登入流程
                    print("\n準備執行登入流程...")
                    page.locator("#login-btn").click()
                    page.wait_for_timeout(300)
                    with page.expect_navigation(wait_until="load", timeout=15000):
                        page.locator('a[ga-data-playload="LogIn"]').click()
                    page.wait_for_timeout(300)

                    page.locator("#login_email").fill(seagm_username)
                    page.wait_for_timeout(300)
                    page.locator("#login_pass").fill(seagm_password)
                    page.wait_for_timeout(300)

                    # 嘗試處理 reCAPTCHA
                    try:
                        recaptcha_frame = page.frame_locator('iframe[title="reCAPTCHA"]')
                        recaptcha_frame.locator("#recaptcha-anchor").click()
                        page.wait_for_timeout(1500)
                    except Exception:
                        print("未找到或無法點擊 reCAPTCHA。")

                    with page.expect_navigation(wait_until="load", timeout=15000):
                         page.locator("#login_btw").click()
                    page.wait_for_timeout(500)

                    print("登入成功！")
                    # 儲存登入狀態
                    context.storage_state(path=auth_file)
                    print(f"登入狀態已儲存至 {auth_file}")

                else:
                    print("偵測到有效的登入狀態，已跳過登入步驟。")

                # 步驟 4: 搜尋遊戲
                print(f"\n正在搜尋遊戲: '{game_name}'")
                search_box = page.locator('input[name="keywords"]')
                search_box.fill(game_name)
                search_box.press("Enter")
                page.wait_for_timeout(500) # 等待搜尋結果加載

                # 步驟 5: 點擊搜尋結果中的遊戲
                print("正在從搜尋結果中定位遊戲連結...")
                # 改為使用更穩定的 href 屬性來定位，避免因語言切換導致 title 變動
                game_link = page.locator('a[href*="identity-v-idv-global-top-up"]')

                expect(game_link).to_be_visible(timeout=15000)
                game_link.click()
                page.wait_for_timeout(500)
                print("已進入商品頁面。")

                # 步驟 6: 在商品頁面完成操作
                print("\n開始在商品頁面進行操作...")

                # 選擇商品 (改為點擊 data-sku，這是更穩定的方式)
                product_selector = f'div[data-sku="{product_id}"]'
                print(f"選擇商品 SKU: {product_id}")
                page.locator(product_selector).click()
                page.wait_for_timeout(300)

                # 輸入玩家ID
                print(f"輸入玩家 ID: {player_id}")
                page.locator('input[name="userid"]').fill(player_id)
                page.wait_for_timeout(300)

                # 選擇伺服器
                print(f"選擇伺服器: {player_server}")
                page.locator('select[name="server"]').select_option(player_server)
                page.wait_for_timeout(300)

                # 點擊立即購買
                print("點擊「立即購買」按鈕...")
                page.locator("#buyNowButton").click()
                page.wait_for_timeout(1000) # 等待一下，讓後續頁面加載
                print("購買流程觸發！")

                print("\n✅ 自動化流程執行完畢。")
                print("5秒後將自動關閉瀏覽器...")
                time.sleep(5)
                return (True, "購買流程已成功觸發。")

            except Exception as e:
                error_message = f"自動化過程中發生未預期的錯誤: {e}"
                print(f"❌ {error_message}")
                return (False, str(e))
            finally:
                print("正在關閉瀏覽器...")
                context.close()
                browser.close()
                print("瀏覽器已關閉。")

if __name__ == '__main__':
    service = PlaywrightService()
    service.run_seagm_automation(
        seagm_username="kk5010760107@gmail.com",
        seagm_password="C5dpLqUC#cq#5Rc",
        game_name="Identity V Echoes(Global)",
        player_id="12345678", # 範例玩家ID
        player_server="Asia",     # 範例伺服器
        product_id="13664"      # 根據您最新提供的值更新
    )
