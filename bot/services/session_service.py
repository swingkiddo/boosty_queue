from repositories.session_repo import SessionRepository
from models.session import Session, SessionRequest, SessionRequestStatus, SessionReview
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from logger import logger
import pandas as pd
from io import BytesIO

class SessionService:
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    async def get_all_sessions(self) -> List[Session]:
        return await self.session_repo.get_all_sessions()
    
    async def get_active_sessions(self) -> List[Session]:
        return await self.session_repo.get_active_sessions()
    
    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_coach_id(coach_id)
    
    async def get_active_sessions_by_user_id(self, user_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_user_id(user_id)
    
    async def get_session_by_id(self, session_id: int) -> Optional[Session]:
        return await self.session_repo.get_by_id(session_id)

    async def get_active_sessions_by_coach_id(self, coach_id: int) -> List[Session]:
        return await self.session_repo.get_active_sessions_by_coach_id(coach_id)

    async def get_last_created_session_by_coach_id(self, coach_id: int) -> Optional[Session]:
        return await self.session_repo.get_last_created_session_by_coach_id(coach_id)
    
    async def create_session(self, coach_id: int, **kwargs) -> Session:
        return await self.session_repo.create(coach_id=coach_id, **kwargs)

    async def update_session(self, session_id: int, **kwargs) -> Session:
        return await self.session_repo.update(session_id, **kwargs)

    async def delete_session(self, session_id: int) -> Session:
        return await self.session_repo.delete(session_id)
    
    async def get_request_by_id(self, request_id: int) -> Optional[SessionRequest]:
        return await self.session_repo.get_request_by_id(request_id)

    async def get_request_by_user_id(self, session_id: int, user_id: int) -> Optional[SessionRequest]:
        return await self.session_repo.get_request_by_user_id(session_id, user_id)

    async def get_accepted_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        requests = await self.get_requests_by_session_id(session_id)
        return [request for request in requests if request.status == SessionRequestStatus.ACCEPTED.value]
    
    async def get_requests_by_session_id(self, session_id: int) -> List[SessionRequest]:
        return await self.session_repo.get_requests_by_session_id(session_id)
    
    async def create_request(self, session_id: int, user_id: int) -> SessionRequest:
        return await self.session_repo.create_request(session_id, user_id, SessionRequestStatus.PENDING.value)
    
    async def update_request_status(self, request_id: int, status: SessionRequestStatus) -> SessionRequest:
        return await self.session_repo.update_request_status(request_id, status.value)
    
    async def delete_request(self, request_id: int) -> SessionRequest:
        return await self.session_repo.delete_request(request_id)

    async def create_review(self, session_id: int, user_id: int, rating: int) -> SessionReview:
        return await self.session_repo.create_review(session_id, user_id, rating=rating)
    
    async def get_reviews_by_session_id(self, session_id: int) -> List[SessionReview]:
        return await self.session_repo.get_reviews_by_session_id(session_id)

    async def get_reviews_by_user_id(self, user_id: int) -> List[SessionReview]:
        return await self.session_repo.get_reviews_by_user_id(user_id)
    
    async def get_review_by_id(self, review_id: int) -> Optional[SessionReview]:
        return await self.session_repo.get_review_by_id(review_id)
    
    async def update_review(self, review_id: int, **kwargs) -> SessionReview:
        return await self.session_repo.update_review(review_id, **kwargs)
    
    async def delete_review(self, review_id: int) -> bool:
        return await self.session_repo.delete_review(review_id)

    async def get_session_data(self, session_id: int) -> Optional[Dict[str, Any]]:
        session = await self.get_session_by_id(session_id)
        if not session:
            return None
        requests = await self.get_requests_by_session_id(session_id)
        reviews = await self.get_reviews_by_session_id(session_id)
        return {
            "session": session,
            "requests": requests,
            "reviews": reviews
        }

    async def prepare_session_report(self, session_id: int) -> Optional[bytes]:
        logger.info(f"Preparing report for session {session_id}")
        session_data = await self.get_session_data(session_id)
        if not session_data:
            return None

        session: Session = session_data["session"]
        requests_list: List[SessionRequest] = session_data["requests"]
        reviews_list: List[SessionReview] = session_data["reviews"]

        logger.info(f"Session: {session}")
        logger.info(f"Requests: {requests_list}")
        logger.info(f"Reviews: {reviews_list}")

        # --- Session Info --- 
        duration_str = "N/A"
        if session.planned_start_time and session.end_time:
            if session.end_time > session.planned_start_time:
                duration: timedelta = session.end_time - session.planned_start_time
                total_seconds = duration.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = "Invalid time range"
        logger.info(f"Session: {session}")
        session_details = {
            "Session ID": session.id,
            "Type": session.type,
            "Coach": session.coach_id,
            "Date": session.date.strftime('%Y-%m-%d %H:%M') if session.date else 'N/A',
            "Planned Start Time": session.planned_start_time.strftime('%Y-%m-%d %H:%M') if session.planned_start_time else 'N/A',
            "End Time": session.end_time.strftime('%Y-%m-%d %H:%M') if session.end_time else 'N/A',
            "Duration": duration_str,
            "Max Slots": session.max_slots,
            "Is Active": session.is_active
        }
        session_info_df = pd.DataFrame([session_details])
        logger.info(f"Session Info: {session_info_df}")
        # --- Requests & Participant Stats --- 
        if requests_list:
            requests_df_data = [
                {"user_id": r.user_id, "status": r.status} for r in requests_list
            ]
            requests_df = pd.DataFrame(requests_df_data)
        else:
            requests_df = pd.DataFrame(columns=["user_id", "status"])

        reviewed_count = len(requests_df[requests_df['status'] == SessionRequestStatus.ACCEPTED.value])
        skipped_count = len(requests_df[requests_df['status'] == SessionRequestStatus.SKIPPED.value])
        rejected_count = len(requests_df[requests_df['status'] == SessionRequestStatus.REJECTED.value])
        pending_count = len(requests_df[requests_df['status'] == SessionRequestStatus.PENDING.value])
        logger.info(f"Reviewed: {reviewed_count}, Skipped: {skipped_count}, Rejected: {rejected_count}, Pending: {pending_count}")
        participant_stats_data = {
            "Category": [
                SessionRequestStatus.ACCEPTED.value.capitalize(), 
                SessionRequestStatus.SKIPPED.value.capitalize(), 
                SessionRequestStatus.REJECTED.value.capitalize(), 
                SessionRequestStatus.PENDING.value.capitalize()
            ],
            "Count": [reviewed_count, skipped_count, rejected_count, pending_count]
        }
        participant_stats_df = pd.DataFrame(participant_stats_data)
        logger.info(f"Participant Stats: {participant_stats_df}")
        # --- Reviews & Review Stats --- 
        if reviews_list:
            reviews_df_data = [
                {"user_id": rev.user_id, "rating": rev.rating} for rev in reviews_list
            ]
            reviews_df = pd.DataFrame(reviews_df_data)
        else:
            reviews_df = pd.DataFrame(columns=["user_id", "rating"])
        logger.info(f"Reviews: {reviews_df}")
        positive_reviews_count = 0
        negative_reviews_count = 0
        neutral_reviews_count = 0
        if not reviews_df.empty:
            positive_reviews_count = len(reviews_df[reviews_df['rating'] >= 4]) # Assuming 4-5 is positive
            negative_reviews_count = len(reviews_df[reviews_df['rating'] <= 2]) # Assuming 1-2 is negative
            neutral_reviews_count = len(reviews_df[reviews_df['rating'] == 3]) # Assuming 3 is neutral

        review_summary_data = {
            "Metric": ["Positive Reviews (4-5)", "Neutral Reviews (3)", "Negative Reviews (1-2)", "Total Reviews"],
            "Count": [positive_reviews_count, neutral_reviews_count, negative_reviews_count, len(reviews_df)]
        }
        review_summary_df = pd.DataFrame(review_summary_data)
        logger.info(f"Review Summary: {review_summary_df}")
        # --- Create Excel --- 
        output = BytesIO()
        logger.info(f"Creating excel writer")
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            session_info_df.to_excel(writer, sheet_name="Session Info", index=False)
            participant_stats_df.to_excel(writer, sheet_name="Participant Stats", index=False)
            review_summary_df.to_excel(writer, sheet_name="Review Stats", index=False)
            logger.info(f"Writing requests to excel")
            if not requests_df.empty:
                requests_df.to_excel(writer, sheet_name="All Requests", index=False)
            else:
                pd.DataFrame([{"message": "No requests for this session"}]).to_excel(writer, sheet_name="All Requests", index=False)
            logger.info(f"Writing reviews to excel")
            if not reviews_df.empty:
                reviews_df.to_excel(writer, sheet_name="All Reviews (User Ratings)", index=False)
            else:
                pd.DataFrame([{"message": "No reviews for this session"}]).to_excel(writer, sheet_name="All Reviews (User Ratings)", index=False)
            logger.info(f"Report created")
        return output.getvalue()

        