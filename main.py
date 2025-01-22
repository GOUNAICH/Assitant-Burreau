import sys
import asyncio
from PyQt6.QtWidgets import QApplication
import qasync
from GraphiqueInterface import MainWindow
from assistant import AIAssistant


async def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Initialisation de l'assistant AI
    assistant = AIAssistant(window)
    assistant.speak("Hello, I'm your AI assistant, Abdo. How can I assist you today?")

    # Boucle principale pour écouter les commandes
    try:
        while True:
            command = await assistant.listen_command()
            if command:
                await assistant.execute_command_async(command)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await loop.create_task(app.exec())

if __name__ == "__main__":
    asyncio.run(main())
