#!/usr/bin/env python3

"""
Менеджер процессов - управление единственным экземпляром бота
"""

import os
import sys
import psutil
import atexit
import signal
from pathlib import Path
from typing import Optional
from config import BotConfig, logger


class ProcessManager:
    """Менеджер для управления единственным экземпляром бота"""

    def __init__(self):
        self.lock_file_path = BotConfig.get_lock_file_path()
        self.lock_file_handle: Optional[object] = None
        self.current_pid = os.getpid()

        # Регистрируем обработчики для корректного завершения
        atexit.register(self.release_lock)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.release_lock()
        sys.exit(0)

    def is_process_running(self, pid: int) -> bool:
        """Проверить, работает ли процесс с данным PID"""
        try:
            return psutil.pid_exists(pid)
        except Exception as e:
            logger.warning(f"Ошибка проверки процесса {pid}: {e}")
            return False

    def acquire_lock(self) -> bool:
        """Получить блокировку для предотвращения множественного запуска"""
        try:
            # Проверяем существующий lock файл
            if self.lock_file_path.exists():
                try:
                    with open(self.lock_file_path, 'r') as f:
                        old_pid = int(f.read().strip())

                    # Проверяем, жив ли старый процесс
                    if self.is_process_running(old_pid):
                        logger.warning(f"Другой экземпляр бота уже запущен (PID: {old_pid})")
                        return False
                    else:
                        # Старый процесс мертв, удаляем lock файл
                        logger.info(f"Удаляем устаревший lock файл (PID: {old_pid})")
                        self.lock_file_path.unlink()

                except (ValueError, IOError) as e:
                    logger.warning(f"Ошибка чтения lock файла: {e}, удаляем его")
                    try:
                        self.lock_file_path.unlink()
                    except:
                        pass

            # Создаем новый lock файл
            self.lock_file_handle = open(self.lock_file_path, 'w')
            self.lock_file_handle.write(str(self.current_pid))
            self.lock_file_handle.flush()

            logger.info(f"Блокировка получена (PID: {self.current_pid})")
            return True

        except Exception as e:
            logger.error(f"Ошибка получения блокировки: {e}")
            return False

    def release_lock(self):
        """Освободить блокировку"""
        try:
            if self.lock_file_handle:
                self.lock_file_handle.close()
                self.lock_file_handle = None

            if self.lock_file_path.exists():
                # Проверяем, что lock файл принадлежит нашему процессу
                try:
                    with open(self.lock_file_path, 'r') as f:
                        file_pid = int(f.read().strip())

                    if file_pid == self.current_pid:
                        self.lock_file_path.unlink()
                        logger.info("Блокировка освобождена")
                    else:
                        logger.warning(f"Lock файл принадлежит другому процессу (PID: {file_pid})")

                except (ValueError, IOError) as e:
                    logger.warning(f"Ошибка при освобождении блокировки: {e}")

        except Exception as e:
            logger.error(f"Ошибка освобождения блокировки: {e}")

    def check_and_acquire_lock(self) -> bool:
        """Проверить и получить блокировку с информативными сообщениями"""
        if not self.acquire_lock():
            print("❌ Другой экземпляр бота уже запущен!")
            print("🔄 Дождитесь его завершения или завершите процесс принудительно.")

            # Попытаемся показать информацию о запущенном процессе
            try:
                if self.lock_file_path.exists():
                    with open(self.lock_file_path, 'r') as f:
                        running_pid = int(f.read().strip())

                    if self.is_process_running(running_pid):
                        try:
                            process = psutil.Process(running_pid)
                            print(f"🔍 Запущенный процесс: PID {running_pid}, команда: {' '.join(process.cmdline())}")
                        except:
                            print(f"🔍 Запущенный процесс: PID {running_pid}")

            except Exception:
                pass

            return False

        return True

    def force_cleanup(self):
        """Принудительная очистка всех lock файлов (для аварийных ситуаций)"""
        try:
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
                print("🧹 Lock файл принудительно удален")
        except Exception as e:
            logger.error(f"Ошибка принудительной очистки: {e}")


# Глобальный экземпляр менеджера процессов
process_manager = ProcessManager()