import logging
import logging.handlers

class Logger(logging.Logger):
    def __init__(self, name: str):
        super().__init__(name)
        self.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        file_handler = logging.handlers.RotatingFileHandler('logs/bot.log', maxBytes=1048576, backupCount=3)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        self.addHandler(handler)
        self.addHandler(file_handler)
        self.info("Logger initialized")

    def info(self, message: str):
        super().info(message)
    
    def error(self, message: str):
        super().error(message)
    
    def warning(self, message: str):
        super().warning(message)
    
    

logger = Logger(__name__)
