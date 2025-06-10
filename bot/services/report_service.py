from services import *
from models import *
from logger import logger
from utils import adapt_db_datetime
import pandas as pd
from discord import Member, User
from typing import List, Dict, Any
from io import BytesIO
import asyncio

class ReportService:
    def __init__(self, bot, coach: Member, participants: List[Member | User], session_data: Dict[str, Any]):
        self.bot = bot
        self.coach = coach
        self.participants = participants
        self.session_data = session_data
        self.session = session_data["session"]
        self.requests = session_data["requests"]
        self.reviews = session_data["reviews"]
        self.activities = session_data["activities"]

    async def create_report(self) -> str:
        try:
            frames = {
                "Сессия": await self.create_session_info_df(),
                "Отзывы": await self.create_report_info_df(),
                "Участники": await self.create_participants_df(),
                "Активность": await self.create_session_activity_df()
            }
            return self.create_report_file(frames)
        except Exception as e:
            logger.error(f"Error creating report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def create_session_info_df(self) -> pd.DataFrame:
        session_info = await self.prepare_session_info()
        session_info_df = pd.DataFrame([session_info])
        return session_info_df

    async def create_report_info_df(self) -> pd.DataFrame:
        report_info = await self.prepare_report_info()
        return pd.DataFrame(data=report_info)
    
    async def create_participants_df(self) -> pd.DataFrame:
        participants_data = await self.prepare_participants_data()
        return pd.DataFrame(data=participants_data)

    async def create_session_activity_df(self) -> pd.DataFrame:
        session_activity_info = await self.prepare_session_activity_info()
        return pd.DataFrame(data=session_activity_info)

    def create_report_file(self, frames: Dict[str, pd.DataFrame]) -> str:
        output = BytesIO()
        filename = f"session_{self.session.id}_report.xlsx"
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in frames.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        output = output.getvalue()
        with open(filename, "wb") as f:
            f.write(output)
        return filename

    async def prepare_participants_data(self) -> Dict[str, Any]:
        reviewed = []
        skipped = []
        for participant in self.participants:
            for req in self.requests:
                if req.user_id == participant.id and req.status == "accepted":
                    reviewed.append(participant)
                if req.user_id == participant.id and req.status == "skipped":
                    skipped.append(participant)
        reviewed_names = [participant.name for participant in reviewed]
        skipped_names = [participant.name for participant in skipped]
        max_len = max(len(reviewed_names), len(skipped_names))

        reviewed_names.extend([None] * (max_len - len(reviewed_names)))
        skipped_names.extend([None] * (max_len - len(skipped_names)))

        data = {
            "Просмотренные": reviewed_names,
            "Пропущенные": skipped_names,
        }
        return data

    async def prepare_report_info(self) -> Dict[str, Any]:
        reviews = [review.to_dict() for review in self.reviews]
        _participants = {participant.id: participant for participant in self.participants}
        review_users = {}
        tasks = []
        for review in reviews:
            if review['user_id'] not in _participants:
                logger.info(f"Review user not in participants: {review['user_id']}")
                _participants[review['user_id']] = await self.bot.fetch_user(review['user_id'])
            _user = _participants[review['user_id']]
            logger.info(f"Review user in participants: {review['user_id']}")
            review_users[review['user_id']] = _user
        if tasks:
            logger.info('tasks')
            _review_users = await asyncio.gather(*tasks)
            for user in _review_users:
                review_users[user.id] = user
        logger.info('reviews')

        likes = []
        dislikes = []
        for review in reviews:
            logger.info(f"Review: {review}")
            if review['user_id'] in review_users:
                _user = review_users[review['user_id']]
                likes.append(_user.name) if review['rating'] else dislikes.append(_user.name)
        max_len = max(len(likes), len(dislikes))
        likes.extend([None] * (max_len - len(likes)))
        dislikes.extend([None] * (max_len - len(dislikes)))
        report_info = {
            "Понравилось": likes,
            "Не понравилось": dislikes
        }
        return report_info
    
    async def prepare_session_info(self) -> Dict[str, Any]:
        reviews = [review.to_dict() for review in self.reviews]
        reviews_df = pd.DataFrame(reviews)
        positive_reviews_count = len(reviews_df[reviews_df['rating'] == 1])
        negative_reviews_count = len(reviews_df[reviews_df['rating'] == 0])
        date = adapt_db_datetime(self.session.date)
        start_time = adapt_db_datetime(self.session.start_time)
        end_time = adapt_db_datetime(self.session.end_time)
        duration = end_time - start_time
        hours = int(duration.total_seconds() // 3600)
        if hours < 10:
            hours = f"0{hours}"
        minutes = int((duration.total_seconds() % 3600) // 60)
        if minutes < 10:
            minutes = f"0{minutes}"
        seconds = int(duration.total_seconds() % 60)
        if seconds < 10:
            seconds = f"0{seconds}"
        duration_str = f"{hours}:{minutes}:{seconds}"
        session_activities = [activity.to_dict() for activity in self.activities]
        unique_ids = []
        for activity in session_activities:
            if activity['user_id'] not in unique_ids:
                unique_ids.append(activity['user_id'])
        session_info = {
            "Сессия": self.session.id,
            "Тип": self.session.type,
            "Коуч": self.coach.name,
            "Дата": date.strftime("%d.%m.%Y") if date else "N/A",
            "Начало": start_time.strftime("%d.%m.%Y %H:%M:%S"),
            "Конец": end_time.strftime("%d.%m.%Y %H:%M:%S"),
            "Длительность": duration_str,
            "Количество слотов": self.session.max_slots,
            "Уникальные участники": len(unique_ids) if unique_ids else "N/A",
            "Положительные реакции": positive_reviews_count,
            "Отрицательные реакции": negative_reviews_count,
        }
        return session_info

    async def prepare_session_activity_info(self) -> Dict[str, Any]:
        voice_channel_state = self.bot.channel_states.get(self.session.voice_channel_id)
        activities = [activity.to_dict() for activity in self.activities]
        activities_df = pd.DataFrame(activities)
        participants_ids = activities_df['user_id'].unique()
        if voice_channel_state:
            unique_users = voice_channel_state['unique_users']
            unique_user_ids = list(unique_users.keys())
        else:
            unique_user_ids = []
        
        data = {
            "Участники": [],
            "Время на сессии": [],
        }
        for participant_id in participants_ids:
            if participant_id in unique_user_ids:
                user = unique_users[participant_id]
            else:
                user = await self.bot.fetch_user(participant_id)
            activities_df['join_time'] = pd.to_datetime(activities_df['join_time'])
            activities_df['leave_time'] = pd.to_datetime(activities_df['leave_time'])
            activities_df['duration'] = activities_df['leave_time'] - activities_df['join_time']
            activities_df['duration'] = activities_df['duration'].dt.total_seconds()
            total_duration = activities_df[activities_df['user_id'] == participant_id]['duration'].sum()
            hours = int(total_duration // 3600)
            if hours < 10:
                hours = f"0{hours}"
            minutes = int((total_duration % 3600) // 60)
            if minutes < 10:
                minutes = f"0{minutes}"
            data["Участники"].append(user.name)
            data["Время на сессии"].append(f"{hours}:{minutes}")
            

        session_activity_df = pd.DataFrame(data)
        logger.info(f"Session activity df: {session_activity_df}")
        return session_activity_df
