from __future__ import annotations

import os
from typing import Any, List

import flet as ft
from openai import OpenAI

# 環境変数からAPIキーを取得
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def adventure_step(story_so_far: str, user_choice: str, hp: int, items: List[str]) -> str:
    prompt = f"""
    あなたは壮大なファンタジー小説の語り部です。
    現在の物語は以下です:
    {story_so_far}

    プレイヤーは「{user_choice}」を選びました。
    プレイヤーの現在のHPは {hp} で、持ち物は {items} です。

    この続きの物語を150〜200文字で語ってください。
    さらに必ず「選択肢を2つ」と「イベント効果」を提示してください。
    イベント効果は HP増減 または アイテム獲得/喪失 の形にしてください。

    形式は:
    ---物語---
    （ストーリー本文）
    ---効果---
    HP: +x / -x または Item: 〇〇
    ---選択肢---
    1. ○○
    2. ○○
    """

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        max_output_tokens=400,
    )
    return response.output_text


def apply_event_effects(story: str, player: dict[str, Any]) -> None:
    if "---効果---" not in story:
        return

    loss_keywords = ["喪失", "失う", "失った", "lost", "失いました"]

    for raw_line in story.splitlines():
        line = raw_line.strip()
        if line.startswith("HP:"):
            effect_text = line.split("HP:", 1)[1].strip()
            if not effect_text:
                continue
            sign = 1
            if effect_text[0] in "+-":
                if effect_text[0] == "-":
                    sign = -1
                effect_text = effect_text[1:]
            try:
                value = int(effect_text.strip())
            except ValueError:
                continue
            player["hp"] += sign * value
        elif line.startswith("Item:"):
            item_text = line.split("Item:", 1)[1].strip()
            if not item_text:
                continue
            is_loss = False
            for keyword in loss_keywords:
                if keyword in item_text:
                    item_text = item_text.replace(keyword, "")
                    is_loss = True
            if item_text.startswith("-"):
                is_loss = True
                item_text = item_text[1:]
            if item_text.startswith("+"):
                item_text = item_text[1:]
            cleaned_item = item_text.strip(" ()")
            if not cleaned_item:
                continue
            if is_loss:
                if cleaned_item in player["items"]:
                    player["items"].remove(cleaned_item)
            elif cleaned_item not in player["items"]:
                player["items"].append(cleaned_item)


def extract_choices(story: str) -> list[str]:
    choices: list[str] = []
    capture = False
    for raw_line in story.splitlines():
        line = raw_line.strip()
        if not capture and line == "---選択肢---":
            capture = True
            continue
        if not capture:
            continue
        if not line:
            if choices:
                break
            continue
        if line[0].isdigit() and "." in line:
            option = line.split(".", 1)[1].strip()
        elif line.startswith("- "):
            option = line[2:].strip()
        else:
            option = line
        if option:
            choices.append(option)
        if len(choices) >= 2:
            break
    return choices


def format_status(player: dict[str, Any]) -> str:
    items = ", ".join(player["items"]) if player["items"] else "なし"
    return f"HP: {player['hp']} / Items: {items}"


def main(page: ft.Page) -> None:
    page.title = "ファンタジーRPGアドベンチャー"
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.padding = 20

    player: dict[str, Any] = {"hp": 20, "items": []}
    initial_story = "あなたは霧深い森の入口に立っている。旅は今始まったばかりだ。"
    story_history: list[str] = [initial_story]
    current_story = initial_story

    story_field = ft.TextField(
        value="\n\n".join(story_history),
        read_only=True,
        multiline=True,
        expand=True,
        min_lines=12,
        max_lines=None,
        label="物語",
    )

    status_text = ft.Text(format_status(player))

    choices_column = ft.Column(spacing=10)

    def update_status() -> None:
        status_text.value = format_status(player)
        status_text.update()

    def update_story_field() -> None:
        story_field.value = "\n\n".join(story_history)
        story_field.update()

    def update_choice_buttons(options: list[str]) -> None:
        choices_column.controls.clear()
        if player["hp"] <= 0:
            choices_column.controls.append(ft.Text("💀 あなたは力尽きてしまった… ゲームオーバー！"))
        elif not options:
            choices_column.controls.append(ft.Text("選択肢がありません。物語はここで幕を閉じます。"))
        else:
            for option in options:
                choices_column.controls.append(
                    ft.ElevatedButton(text=option, on_click=lambda e, opt=option: handle_choice(opt))
                )
        choices_column.update()

    def handle_choice(choice_text: str) -> None:
        nonlocal current_story
        if player["hp"] <= 0:
            return
        try:
            new_story = adventure_step(current_story, choice_text, player["hp"], player["items"])
        except Exception as exc:  # noqa: BLE001
            page.snack_bar = ft.SnackBar(ft.Text(f"物語の生成に失敗しました: {exc}"), open=True)
            page.update()
            return

        current_story = new_story
        story_history.append(new_story)
        update_story_field()

        apply_event_effects(new_story, player)
        update_status()

        if player["hp"] <= 0:
            update_choice_buttons([])
            return

        update_choice_buttons(extract_choices(new_story))

    initial_choices = ["森の奥へ進む", "焚き火を起こして準備する"]
    update_choice_buttons(initial_choices)

    page.add(
        ft.Column(
            controls=[
                ft.Text("ファンタジーRPGアドベンチャー", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                story_field,
                ft.Text("次の行動を選んでください:"),
                choices_column,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("ステータス", style=ft.TextThemeStyle.TITLE_MEDIUM),
                            status_text,
                        ],
                        tight=True,
                    ),
                    bgcolor=ft.colors.with_opacity(0.05, ft.colors.BLUE_GREY),
                    padding=ft.padding.all(12),
                    border_radius=8,
                ),
            ],
            expand=True,
            spacing=16,
        )
    )


if __name__ == "__main__":
    ft.app(target=main)

