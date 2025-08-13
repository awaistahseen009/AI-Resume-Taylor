import os
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

class MessageGenerator:
    """Service for generating personalized outreach messages"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=os.environ.get('OPENAI_API_KEY')
        )
    
    def generate_message(self, job_description: str, company: str, job_title: str, 
                        message_type: str, tone: str = "professional", 
                        user_name: str = "") -> Dict[str, str]:
        """Generate outreach message based on job details"""
        
        if message_type == "email":
            return self._generate_email(job_description, company, job_title, tone, user_name)
        elif message_type == "linkedin":
            return self._generate_linkedin_message(job_description, company, job_title, tone, user_name)
        elif message_type == "pitch":
            return self._generate_elevator_pitch(job_description, company, job_title, tone, user_name)
        else:
            raise ValueError(f"Unsupported message type: {message_type}")
    
    def _generate_email(self, job_description: str, company: str, job_title: str, 
                       tone: str, user_name: str) -> Dict[str, str]:
        """Generate professional email to hiring manager"""
        
        system_prompt = f"""
        You are an expert at writing professional, personalized outreach emails for job applications.
        Create an email that is {tone}, engaging, and shows genuine interest in the role.
        
        Guidelines:
        - Keep it concise (150-200 words)
        - Show you've researched the company and role
        - Highlight relevant skills without being pushy
        - Include a clear call-to-action
        - Use proper email formatting
        """
        
        human_prompt = f"""
        Write a professional email for a job application with these details:
        
        Job Title: {job_title}
        Company: {company}
        Applicant Name: {user_name or "the applicant"}
        Tone: {tone}
        
        Job Description (key points):
        {job_description[:1000]}  # Limit to avoid token limits
        
        Include:
        1. Compelling subject line
        2. Professional greeting
        3. Brief introduction and interest statement
        4. 2-3 key qualifications that match the role
        5. Mention of attached resume
        6. Professional closing with call-to-action
        
        Format as:
        Subject: [subject line]
        
        [email body]
        """
        
        try:
            response = self.llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            # Parse subject and body
            content = response.content.strip()
            lines = content.split('\n')
            
            subject = ""
            body = ""
            
            for i, line in enumerate(lines):
                if line.startswith("Subject:"):
                    subject = line.replace("Subject:", "").strip()
                    body = '\n'.join(lines[i+1:]).strip()
                    break
            
            if not subject:
                # Fallback if format is different
                subject = f"Application for {job_title} Position at {company}"
                body = content
            
            return {
                'subject': subject,
                'content': body,
                'tips': [
                    "Research the hiring manager's name if possible",
                    "Send during business hours (9 AM - 5 PM)",
                    "Follow up after 1-2 weeks if no response",
                    "Keep attachments under 5MB"
                ]
            }
            
        except Exception as e:
            return self._generate_fallback_email(job_title, company, user_name)
    
    def _generate_linkedin_message(self, job_description: str, company: str, 
                                  job_title: str, tone: str, user_name: str) -> Dict[str, str]:
        """Generate LinkedIn connection/message"""
        
        system_prompt = f"""
        You are an expert at writing engaging LinkedIn messages for professional networking.
        Create a message that is {tone}, concise, and builds genuine connection.
        
        Guidelines:
        - Keep it very short (50-100 words for connection request, 100-150 for message)
        - Be personable and authentic
        - Show genuine interest in their work/company
        - Avoid being too salesy
        - Include a soft ask or conversation starter
        """
        
        human_prompt = f"""
        Write a LinkedIn message for networking about this job opportunity:
        
        Job Title: {job_title}
        Company: {company}
        Sender: {user_name or "the job seeker"}
        Tone: {tone}
        
        Job Description highlights:
        {job_description[:800]}
        
        Create both:
        1. Connection request message (50 words max)
        2. Follow-up message after connection (100-150 words)
        
        Format as:
        Connection Request:
        [message]
        
        Follow-up Message:
        [message]
        """
        
        try:
            response = self.llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            content = response.content.strip()
            
            # Parse connection request and follow-up
            parts = content.split("Follow-up Message:")
            connection_msg = parts[0].replace("Connection Request:", "").strip()
            followup_msg = parts[1].strip() if len(parts) > 1 else ""
            
            full_message = f"Connection Request:\n{connection_msg}\n\nFollow-up Message:\n{followup_msg}"
            
            return {
                'subject': f"Connection Request - {job_title} Opportunity",
                'content': full_message,
                'tips': [
                    "Personalize with something from their profile",
                    "Connect on Tuesday-Thursday for best response rates",
                    "Don't pitch immediately after connecting",
                    "Engage with their posts before reaching out"
                ]
            }
            
        except Exception as e:
            return self._generate_fallback_linkedin(job_title, company, user_name)
    
    def _generate_elevator_pitch(self, job_description: str, company: str, 
                               job_title: str, tone: str, user_name: str) -> Dict[str, str]:
        """Generate elevator pitch for networking events"""
        
        system_prompt = f"""
        You are an expert at crafting compelling elevator pitches for job seekers.
        Create a pitch that is {tone}, memorable, and clearly communicates value.
        
        Guidelines:
        - 30-60 seconds when spoken (100-150 words)
        - Start with a hook or interesting fact
        - Clearly state what you do and what you're looking for
        - Include specific skills/achievements
        - End with a question or call-to-action
        """
        
        human_prompt = f"""
        Create an elevator pitch for someone seeking this role:
        
        Target Job: {job_title}
        Target Company: {company}
        Speaker: {user_name or "the job seeker"}
        Tone: {tone}
        
        Job Requirements/Description:
        {job_description[:800]}
        
        Structure:
        1. Hook/Introduction (who you are)
        2. What you do (current role/skills)
        3. What you're looking for (target role)
        4. Value proposition (what you bring)
        5. Call-to-action (question/next step)
        
        Keep it conversational and natural.
        """
        
        try:
            response = self.llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ])
            
            return {
                'subject': f"Elevator Pitch - {job_title}",
                'content': response.content.strip(),
                'tips': [
                    "Practice until it sounds natural",
                    "Adjust based on your audience",
                    "Have 30-second and 60-second versions",
                    "End with a question to start conversation",
                    "Be enthusiastic but not overwhelming"
                ]
            }
            
        except Exception as e:
            return self._generate_fallback_pitch(job_title, company, user_name)
    
    def _generate_fallback_email(self, job_title: str, company: str, user_name: str) -> Dict[str, str]:
        """Fallback email template if AI generation fails"""
        subject = f"Application for {job_title} Position"
        
        body = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. After reviewing the job description, I am excited about the opportunity to contribute to your team.

My background in [relevant field] and experience with [key skills] align well with the requirements outlined in the posting. I am particularly drawn to [specific aspect of the role/company] and believe my skills in [specific skills] would be valuable to your organization.

I have attached my resume for your review and would welcome the opportunity to discuss how my experience can benefit {company}. Thank you for considering my application.

Best regards,
{user_name or '[Your Name]'}"""

        return {
            'subject': subject,
            'content': body,
            'tips': ["Customize the bracketed sections with your specific details"]
        }
    
    def _generate_fallback_linkedin(self, job_title: str, company: str, user_name: str) -> Dict[str, str]:
        """Fallback LinkedIn message if AI generation fails"""
        content = f"""Connection Request:
Hi! I noticed you work at {company} and I'm very interested in opportunities there, particularly in {job_title} roles. I'd love to connect and learn more about your experience at the company.

Follow-up Message:
Thanks for connecting! I'm currently exploring {job_title} opportunities and am really impressed by {company}'s work. I'd love to hear about your experience there and any insights you might have about the team. Would you be open to a brief chat sometime?"""

        return {
            'subject': f"LinkedIn Outreach - {job_title}",
            'content': content,
            'tips': ["Personalize based on their profile and recent posts"]
        }
    
    def _generate_fallback_pitch(self, job_title: str, company: str, user_name: str) -> Dict[str, str]:
        """Fallback elevator pitch if AI generation fails"""
        content = f"""Hi, I'm {user_name or '[Your Name]'}. I'm a [your profession] with [X years] of experience in [relevant field]. 

I specialize in [key skills] and have a track record of [specific achievement]. I'm currently looking for {job_title} opportunities where I can apply my expertise in [relevant area].

I'm particularly interested in companies like {company} because of [reason]. I'd love to learn more about opportunities in this space - do you know anyone I should connect with?"""

        return {
            'subject': f"Elevator Pitch - {job_title}",
            'content': content,
            'tips': ["Fill in the bracketed sections with your specific details"]
        }
