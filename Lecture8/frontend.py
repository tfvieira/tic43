from typing import Dict, List, Any
from nicegui import ui
import traceback
import requests
import asyncio

from variables import (
    BACKEND_URL,
    PRIMARY_COLOR,
    SECONDARY_COLOR,
    NEGATIVE_COLOR,
    POSITIVE_COLOR,
    BACKGROUND_COLOR,
    CARD_BACKGROUND_COLOR,
    TEXT_PRIMARY_COLOR,
    TEXT_SECONDARY_COLOR,
    BORDER_COLOR,
)


class TaskParameter:
    """
    Model for task parameter definition.
    """

    def __init__(self, name: str) -> None:
        """
        Initialize task parameter.
        :param name: Parameter name.
        """
        self.name = name


class Task:
    """
    Model for task representation.
    """

    def __init__(
        self, id: int, name: str, system_prompt: str, parameters: List[TaskParameter]
    ) -> None:
        """
        Initialize task.
        :param id: Task ID.
        :param name: Task name.
        :param system_prompt: Task system prompt.
        :param parameters: Task parameters.
        """
        self.id = id
        self.name = name
        self.system_prompt = system_prompt
        self.parameters = parameters


class TaskManager:
    """
    Task management interface using NiceGUI.
    """

    def __init__(self) -> None:
        """
        Initialize the task manager.
        """
        self.tasks: List[Task] = []
        self.current_page = 0
        self.items_per_page = 10
        self.total_tasks = 0

        # UI element references
        self.task_table = None
        self.pagination_info = None
        self.loading_spinner = None
        self.prev_button = None
        self.next_button = None

    async def _perform_request(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """
        A wrapper for requests to handle async execution in NiceGUI.
        :param method: HTTP method ('get', 'post', 'patch', 'delete').
        :param url: The URL for the request.
        :param kwargs: Additional arguments for the requests call.
        :return: The response object.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: requests.request(method, url, **kwargs)
        )

    async def fetch_tasks(self) -> None:
        """
        Fetch tasks from the backend.
        """
        try:
            if self.loading_spinner:
                self.loading_spinner.set_visibility(True)

            response = await self._perform_request(
                "get", f"{BACKEND_URL}/api/v1/tasks/list"
            )
            response.raise_for_status()

            tasks_data = response.json()
            self.tasks = [
                Task(
                    id=task_data["id"],
                    name=task_data["name"],
                    system_prompt=task_data["system_prompt"],
                    parameters=[
                        TaskParameter(p["name"]) for p in task_data["parameters"]
                    ],
                )
                for task_data in tasks_data
            ]
            self.total_tasks = len(self.tasks)
            # Reset to first page if the task list changes significantly
            if self.current_page * self.items_per_page >= self.total_tasks:
                self.current_page = 0

        except requests.RequestException as e:
            traceback.print_exc()
            ui.notify(
                f"Failed to fetch tasks: {e}", type="negative", color=NEGATIVE_COLOR
            )
        finally:
            if self.loading_spinner:
                self.loading_spinner.set_visibility(False)

    def get_paginated_tasks(self) -> List[Task]:
        """
        Get tasks for the current page.
        """
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.tasks[start_idx:end_idx]

    async def create_task(
        self,
        name: str,
        system_prompt: str,
        parameter_names: List[str],
        dialog: ui.dialog,
    ) -> None:
        """
        Create a new task.
        """
        loading_spinner = dialog.parent_slot.parent.default_slot.children[2]
        try:
            loading_spinner.set_visibility(True)
            parameters = [
                {"name": param_name}
                for param_name in parameter_names
                if param_name.strip()
            ]
            task_data = {
                "name": name,
                "system_prompt": system_prompt,
                "parameters": parameters,
            }

            response = await self._perform_request(
                "post", f"{BACKEND_URL}/api/v1/tasks/create", json=task_data
            )
            response.raise_for_status()

            ui.notify(
                "Task created successfully!", type="positive", color=POSITIVE_COLOR
            )
            await self.refresh_tasks()
            dialog.close()

        except requests.RequestException as e:
            traceback.print_exc()
            ui.notify(
                f"Failed to create task: {e}", type="negative", color=NEGATIVE_COLOR
            )
        finally:
            loading_spinner.set_visibility(False)

    async def edit_task(
        self,
        task_id: int,
        name: str,
        system_prompt: str,
        parameter_names: List[str],
        dialog: ui.dialog,
    ) -> None:
        """
        Edit an existing task.
        """
        loading_spinner = dialog.parent_slot.parent.default_slot.children[2]
        try:
            loading_spinner.set_visibility(True)
            parameters = [
                {"name": param_name}
                for param_name in parameter_names
                if param_name.strip()
            ]
            task_data = {
                "name": name,
                "system_prompt": system_prompt,
                "parameters": parameters,
            }

            response = await self._perform_request(
                "patch", f"{BACKEND_URL}/api/v1/tasks/edit/{task_id}", json=task_data
            )
            response.raise_for_status()

            ui.notify(
                "Task updated successfully!", type="positive", color=POSITIVE_COLOR
            )
            await self.refresh_tasks()
            dialog.close()

        except requests.RequestException as e:
            traceback.print_exc()
            ui.notify(
                f"Failed to update task: {e}", type="negative", color=NEGATIVE_COLOR
            )
        finally:
            loading_spinner.set_visibility(False)

    async def delete_task(self, task_id: int, dialog: ui.dialog) -> None:
        """
        Delete a task.
        """
        loading_spinner = dialog.parent_slot.parent.default_slot.children[1]
        try:
            loading_spinner.set_visibility(True)
            response = await self._perform_request(
                "delete", f"{BACKEND_URL}/api/v1/tasks/delete/{task_id}"
            )
            response.raise_for_status()

            ui.notify(
                "Task deleted successfully!", type="positive", color=POSITIVE_COLOR
            )
            await self.refresh_tasks()
            dialog.close()

        except requests.RequestException as e:
            traceback.print_exc()
            ui.notify(
                f"Failed to delete task: {e}", type="negative", color=NEGATIVE_COLOR
            )
        finally:
            loading_spinner.set_visibility(False)

    async def execute_task(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        loading_spinner: ui.spinner,
        result_container: ui.element,
    ) -> None:
        """
        Execute a task with given parameters.
        """
        try:
            loading_spinner.set_visibility(True)
            result_container.clear()

            response = await self._perform_request(
                "post",
                f"{BACKEND_URL}/api/v1/tasks/execute",
                params={"task_name": task_name},
                json=parameters,
            )
            response.raise_for_status()
            result = response.json()

            with result_container:
                with ui.card().classes("w-full").style(
                    f"background-color: {BACKGROUND_COLOR}; border: 1px solid {BORDER_COLOR}"
                ):
                    ui.markdown(result["result"]).style(
                        f"color: {TEXT_SECONDARY_COLOR}"
                    )

        except requests.RequestException as e:
            traceback.print_exc()
            with result_container:
                with ui.card().classes("w-full").style(
                    f"background-color: #fff0f0; border: 1px solid {NEGATIVE_COLOR}"
                ):
                    ui.label("Execution Error").classes(
                        "text-lg font-medium text-red-800"
                    )
                    ui.separator()
                    ui.label(f"Failed to execute task: {e}").classes(
                        "mt-2 text-red-700"
                    )
        finally:
            loading_spinner.set_visibility(False)

    async def refresh_tasks(self) -> None:
        """
        Refresh the task list and update UI.
        """
        await self.fetch_tasks()
        self.update_task_table()
        self.update_pagination()

    def update_task_table(self) -> None:
        """
        Update the task table display.
        """
        if self.task_table:
            self.task_table.clear()
            with self.task_table:
                self.create_task_table_content()

    def update_pagination(self) -> None:
        """
        Update pagination information and button states.
        """
        if self.pagination_info:
            total_pages = (
                self.total_tasks + self.items_per_page - 1
            ) // self.items_per_page
            total_pages = max(1, total_pages)
            self.pagination_info.text = f"Page {self.current_page + 1} of {total_pages} ({self.total_tasks} tasks)"

            if self.prev_button and self.next_button:
                self.prev_button.set_enabled(self.current_page > 0)
                self.next_button.set_enabled(self.current_page < total_pages - 1)

    def next_page(self) -> None:
        """
        Navigate to the next page.
        """
        total_pages = (
            self.total_tasks + self.items_per_page - 1
        ) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_task_table()
            self.update_pagination()

    def prev_page(self) -> None:
        """
        Navigate to the previous page.
        """
        if self.current_page > 0:
            self.current_page -= 1
            self.update_task_table()
            self.update_pagination()

    # --- UI Dialogs ---

    def _create_dialog_card(self, title: str) -> ui.card:
        """Helper to create a styled dialog card."""
        card = ui.card().classes("w-full").style("min-width: 60vw; max-width: 70vw;")
        with card:
            ui.label(title).classes("text-h5 mb-4").style(
                f"color: {TEXT_PRIMARY_COLOR}"
            )
            ui.separator()
        return card

    def show_create_task_dialog(self) -> None:
        """
        Show the dialog for creating a new task.
        """
        with ui.dialog() as dialog, self._create_dialog_card("Create New Task"):
            name_input = ui.input(
                "Task Name", placeholder="Enter a descriptive task name"
            ).classes("w-full mb-4")
            prompt_input = (
                ui.textarea(
                    "System Prompt",
                    placeholder="Describe the LLM's role and instructions...",
                )
                .classes("w-full mb-4")
                .props("outlined")
            )

            ui.label("Task Parameters").classes("text-h6 mb-2")
            param_container = ui.column().classes("w-full gap-2")
            param_inputs = []

            def add_parameter(init_val: str = ""):
                with param_container:
                    with ui.row().classes("w-full items-center no-wrap"):
                        param_input = ui.input(
                            "Parameter Name",
                            placeholder="e.g., user_input, topic",
                            value=init_val,
                        ).classes("flex-grow")
                        param_inputs.append(param_input)
                        ui.button(
                            icon="remove_circle_outline",
                            on_click=lambda: remove_parameter(param_input.parent),
                        ).props("flat round").style(f"color: {NEGATIVE_COLOR}")

            def remove_parameter(row_to_remove: ui.row):
                # Find the input to remove from the list
                input_to_remove = next(
                    (inp for inp in param_inputs if inp.parent == row_to_remove), None
                )
                if input_to_remove:
                    param_inputs.remove(input_to_remove)
                row_to_remove.delete()

            ui.button(
                "Add Parameter", icon="add", on_click=add_parameter, color=PRIMARY_COLOR
            ).props("outline").classes("my-4")

            loading_spinner = ui.spinner(size="lg", color=PRIMARY_COLOR).classes(
                "mx-auto my-4"
            )
            loading_spinner.set_visibility(False)

            ui.separator()
            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Create Task",
                    on_click=lambda: self.handle_create_task(
                        dialog,
                        name_input.value,
                        prompt_input.value,
                        [inp.value for inp in param_inputs],
                    ),
                    color=PRIMARY_COLOR,
                )

        dialog.open()

    async def handle_create_task(
        self, dialog: ui.dialog, name: str, prompt: str, param_names: List[str]
    ):
        if not name.strip() or not prompt.strip():
            ui.notify(
                "Task Name and System Prompt are required.",
                type="negative",
                color=NEGATIVE_COLOR,
            )
            return
        await self.create_task(name.strip(), prompt.strip(), param_names, dialog)

    def show_edit_task_dialog(self, task: Task) -> None:
        """
        Show the dialog for editing an existing task.
        """
        with ui.dialog() as dialog, self._create_dialog_card(f"Edit Task: {task.name}"):
            name_input = ui.input("Task Name", value=task.name).classes("w-full mb-4")
            prompt_input = (
                ui.textarea("System Prompt", value=task.system_prompt)
                .classes("w-full mb-4")
                .props("outlined")
            )

            ui.label("Task Parameters").classes("text-h6 mb-2")
            param_container = ui.column().classes("w-full gap-2")
            param_inputs = []

            def add_parameter(init_val: str = ""):
                with param_container:
                    with ui.row().classes("w-full items-center no-wrap"):
                        param_input = ui.input(
                            "Parameter Name", value=init_val
                        ).classes("flex-grow")
                        param_inputs.append(param_input)
                        ui.button(
                            icon="remove_circle_outline",
                            on_click=lambda: remove_parameter(param_input.parent),
                        ).props("flat round").style(f"color: {NEGATIVE_COLOR}")

            def remove_parameter(row_to_remove: ui.row):
                input_to_remove = next(
                    (inp for inp in param_inputs if inp.parent == row_to_remove), None
                )
                if input_to_remove:
                    param_inputs.remove(input_to_remove)
                row_to_remove.delete()

            for p in task.parameters:
                add_parameter(p.name)

            ui.button(
                "Add Parameter",
                icon="add",
                on_click=lambda: add_parameter(),
                color=PRIMARY_COLOR,
            ).props("outline").classes("my-4")

            loading_spinner = ui.spinner(size="lg", color=PRIMARY_COLOR).classes(
                "mx-auto my-4"
            )
            loading_spinner.set_visibility(False)

            ui.separator()
            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Save Changes",
                    on_click=lambda: self.handle_edit_task(
                        dialog,
                        task.id,
                        name_input.value,
                        prompt_input.value,
                        [inp.value for inp in param_inputs],
                    ),
                    color=PRIMARY_COLOR,
                ).style("color: #FFFFFF")

        dialog.open()

    async def handle_edit_task(
        self,
        dialog: ui.dialog,
        task_id: int,
        name: str,
        prompt: str,
        param_names: List[str],
    ):
        if not name.strip() or not prompt.strip():
            ui.notify(
                "Task Name and System Prompt are required.",
                type="negative",
                color=NEGATIVE_COLOR,
            )
            return
        await self.edit_task(task_id, name.strip(), prompt.strip(), param_names, dialog)

    def show_delete_confirmation(self, task: Task) -> None:
        """
        Show a confirmation dialog before deleting a task.
        """
        with ui.dialog() as dialog, ui.card().style("min-width: 400px;"):
            ui.label("Confirm Deletion").classes("text-h6")
            ui.separator()
            ui.label(
                f"Are you sure you want to delete the task '{task.name}'?"
            ).classes("my-4")
            ui.label("This action cannot be undone.").style(
                f"color: {NEGATIVE_COLOR}; font-weight: bold;"
            )

            loading_spinner = ui.spinner(size="lg", color=PRIMARY_COLOR).classes(
                "mx-auto my-4"
            )
            loading_spinner.set_visibility(False)

            ui.separator()
            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button(
                    "Delete",
                    on_click=lambda: self.delete_task(task.id, dialog),
                    color=NEGATIVE_COLOR,
                ).style("color: #FFFFFF")
        dialog.open()

    def show_execute_task_dialog(self, task: Task) -> None:
        """
        Show the dialog for executing a task.
        """
        with ui.dialog() as dialog, self._create_dialog_card(
            f"Execute Task: {task.name}"
        ):
            with ui.splitter().classes("w-full h-full").style(
                "min-height: 60vh;"
            ) as splitter:
                with splitter.before:
                    with ui.column().classes("p-4 w-full"):
                        ui.label("System Prompt").classes("text-h6 mb-2")
                        with ui.card().classes("w-full p-2").style(
                            f"background-color: {BACKGROUND_COLOR}; border: 1px solid {BORDER_COLOR}; max-height: 150px; overflow-y: auto;"
                        ):
                            ui.add_css(
                                """
                                pre code {
                                    white-space: pre-wrap;
                                    word-break: break-word;
                                }
                                """
                            )
                            ui.code(task.system_prompt, language="xml")

                        ui.separator().classes("my-4")

                        ui.label("Parameters").classes("text-h6 mb-2")
                        param_inputs = {}
                        if task.parameters:
                            for param in task.parameters:
                                param_inputs[param.name] = (
                                    ui.input(
                                        param.name,
                                        placeholder=f"Enter value for {param.name}...",
                                    )
                                    .classes("w-full")
                                    .props("outlined")
                                )
                        else:
                            ui.label("This task has no parameters.").classes(
                                "text-sm"
                            ).style(f"color: {TEXT_SECONDARY_COLOR}")

                with splitter.after:
                    with ui.column().classes("p-4 w-full"):
                        ui.label("Execution").classes("text-h6 mb-2")
                        loading_spinner = ui.spinner(
                            size="xl", color=PRIMARY_COLOR
                        ).classes("mx-auto my-8")
                        loading_spinner.set_visibility(False)
                        result_container = ui.column().classes("w-full")

            ui.separator()
            with ui.row().classes("w-full justify-end p-4 bg-white"):
                ui.button("Close", on_click=dialog.close).props("flat")
                ui.button(
                    "Execute",
                    icon="play_arrow",
                    on_click=lambda: self.handle_execute_task(
                        task.name,
                        {name: inp.value for name, inp in param_inputs.items()},
                        loading_spinner,
                        result_container,
                    ),
                    color=PRIMARY_COLOR,
                ).style("color: #FFFFFF")
        dialog.open()

    async def handle_execute_task(
        self,
        task_name: str,
        parameters: Dict[str, str],
        loading_spinner: ui.spinner,
        result_container: ui.element,
    ):
        if any(not value.strip() for value in parameters.values()):
            ui.notify(
                "All parameters are required.", type="negative", color=NEGATIVE_COLOR
            )
            return
        await self.execute_task(
            task_name, parameters, loading_spinner, result_container
        )

    # --- Main Page Layout ---

    def create_task_table_content(self) -> None:
        """
        Create the content for the task table.
        """
        paginated_tasks = self.get_paginated_tasks()

        if not paginated_tasks:
            with ui.card().classes("w-full text-center p-8"):
                ui.icon("inbox", size="xl").style(f"color: {TEXT_SECONDARY_COLOR}")
                ui.label("No tasks found.").classes("text-lg mt-4").style(
                    f"color: {TEXT_SECONDARY_COLOR}"
                )
                ui.label("Click 'Create Task' to get started.").classes(
                    "text-sm"
                ).style(f"color: {TEXT_SECONDARY_COLOR}")
            return

        # Table Header
        with ui.row().classes("w-full p-2").style(
            f"background-color: {BACKGROUND_COLOR}; border-bottom: 2px solid {BORDER_COLOR}"
        ):
            ui.label("Name").classes("font-bold").style("flex: 2")
            ui.label("Prompt Snippet").classes("font-bold").style("flex: 3")
            ui.label("Parameters").classes("font-bold").style("flex: 2")
            ui.label("Actions").classes("font-bold text-center").style("flex: 2")

        # Table Rows
        for task in paginated_tasks:
            with ui.row().classes("w-full items-center p-2 hover:bg-gray-100"):
                ui.label(task.name).classes("font-medium").style("flex: 2")

                prompt_text = (
                    (task.system_prompt[:50] + "...")
                    if len(task.system_prompt) > 50
                    else task.system_prompt
                )
                ui.label(prompt_text).classes("text-sm").style(
                    f"color: {TEXT_SECONDARY_COLOR}; flex: 3"
                )

                if task.parameters:
                    param_names = ", ".join([p.name for p in task.parameters])
                    ui.label(param_names).classes("text-sm").style("flex: 2")
                else:
                    ui.label("None").classes("text-sm").style(
                        f"color: {TEXT_SECONDARY_COLOR}; flex: 2"
                    )

                with ui.row().classes("justify-center").style("flex: 2"):
                    ui.button(
                        icon="play_arrow",
                        on_click=lambda t=task: self.show_execute_task_dialog(t),
                    ).props("flat round").style(f"color: {POSITIVE_COLOR}").tooltip(
                        "Execute"
                    )
                    ui.button(
                        icon="edit",
                        on_click=lambda t=task: self.show_edit_task_dialog(t),
                    ).props("flat round").style(f"color: {SECONDARY_COLOR}").tooltip(
                        "Edit"
                    )
                    ui.button(
                        icon="delete",
                        on_click=lambda t=task: self.show_delete_confirmation(t),
                    ).props("flat round").style(f"color: {NEGATIVE_COLOR}").tooltip(
                        "Delete"
                    )
            ui.separator()

    def create_main_page(self) -> None:
        """
        Create the main page layout.
        """
        ui.colors(primary=PRIMARY_COLOR)

        with ui.header(elevated=True).classes("items-center justify-between p-2").style(
            f"background-color: {CARD_BACKGROUND_COLOR}; color: {TEXT_PRIMARY_COLOR}"
        ):
            ui.label("Task Manager").classes("text-2xl font-bold")
            with ui.row().classes("items-center"):
                ui.button(
                    "Create Task",
                    icon="add",
                    on_click=self.show_create_task_dialog,
                    color=PRIMARY_COLOR,
                ).style("color: #FFFFFF")

        with ui.column().classes("w-full max-w-7xl mx-auto p-4 lg:p-8"):
            self.loading_spinner = ui.spinner(size="xl", color=PRIMARY_COLOR).classes(
                "mx-auto my-16"
            )

            with ui.card().classes("w-full p-0"):
                self.task_table = ui.column().classes("w-full")

            with ui.row().classes("w-full justify-between items-center mt-4"):
                self.prev_button = ui.button(
                    "Previous", icon="chevron_left", on_click=self.prev_page
                ).props("flat")
                self.pagination_info = ui.label("")
                self.next_button = ui.button(
                    "Next", icon="chevron_right", on_click=self.next_page
                ).props("flat")

        asyncio.create_task(self.refresh_tasks())


# --- App Initialization ---

task_manager = TaskManager()


@ui.page("/")
def main_page_route():
    """
    Main page route.
    """
    task_manager.create_main_page()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Task Manager",
        favicon="🚀",
        native=True,
        window_size=(1440, 900),
        fullscreen=False,
        reload=True,
    )
