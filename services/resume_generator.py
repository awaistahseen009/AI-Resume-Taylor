import openai
import json
import logging
from typing import Dict, Any
from services.resume_schema import ResumeData
from flask import current_app

class ResumeContentGenerator:
    """Generate resume content using OpenAI function calling with Pydantic schemas."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=current_app.config.get('OPENAI_API_KEY'))
    
    def generate_resume_content(self, job_description: str, existing_resume_text: str = "") -> ResumeData:
        """
        Generate structured resume content based on job description and existing resume.
        
        Args:
            job_description: The target job description
            existing_resume_text: Existing resume content to tailor
            
        Returns:
            ResumeData: Structured resume data
        """
        try:
            # Create the function schema from Pydantic model
            function_schema = {
                "name": "generate_resume_content",
                "description": "Generate structured resume content tailored to a job description",
                "parameters": ResumeData.model_json_schema()
            }
            
            # Prepare the prompt
            system_prompt = """You are an expert resume writer. Generate comprehensive resume content based on the job description and existing resume information provided. 

Key requirements:
- Tailor content to match the job requirements
- Use professional language and action verbs
- Include specific achievements and metrics where possible
- Ensure all sections are relevant and well-structured
- Make the content compelling and ATS-friendly
- Do not use any emojis or special characters
- Keep descriptions concise but impactful"""

            user_prompt = f"""
Job Description:
{job_description}

Existing Resume Content:
{existing_resume_text}

Please generate a complete, tailored resume structure that matches this job description. Include all relevant sections with specific, professional content. If existing resume content is provided, enhance and tailor it to the job description.
"""

            # Make the API call with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                functions=[function_schema],
                function_call={"name": "generate_resume_content"},
                temperature=0.7
            )
            
            # Extract function call result
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "generate_resume_content":
                resume_data_json = json.loads(function_call.arguments)
                return ResumeData(**resume_data_json)
            else:
                raise ValueError("No function call response received")
                
        except Exception as e:
            logging.error(f"Error generating resume content: {e}")
            # Return a basic template with placeholders if generation fails
            return self._get_fallback_resume_data()
    
    def _get_fallback_resume_data(self) -> ResumeData:
        """Return fallback resume data with placeholders."""
        from services.resume_schema import ContactInfo, EducationEntry, ExperienceEntry
        
        return ResumeData(
            contact_info=ContactInfo(
                name="[Your Name]",
                location="[Location]",
                email="[email@example.com]",
                phone="[+1234567890]",
                website="[website-url]",
                linkedin="[linkedin-url]",
                github="[github-url]"
            ),
            about_me="[Your about me description]",
            education=[
                EducationEntry(
                    dates="[Dates]",
                    institution="[Institution]",
                    degree="[Degree]",
                    highlights=["[Highlight 1]", "[Highlight 2]"]
                )
            ],
            experience=[
                ExperienceEntry(
                    dates="[Dates]",
                    job_title="[Job Title]",
                    company="[Company]",
                    responsibilities=["[Responsibility 1]", "[Responsibility 2]"]
                )
            ],
            languages="[Language details]",
            skills="[Skill details]",
            volunteering="[Volunteering details]",
            interests="[Interests details]"
        )
