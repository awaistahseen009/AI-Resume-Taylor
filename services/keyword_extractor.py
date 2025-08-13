import re
from typing import List, Dict, Set
from collections import Counter
import string

class KeywordExtractor:
    """Service for extracting keywords and skills from job descriptions"""
    
    def __init__(self):
        # Common technical skills and keywords
        self.technical_skills = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
                'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql'
            ],
            'frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express',
                'laravel', 'rails', 'asp.net', 'tensorflow', 'pytorch', 'scikit-learn'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sqlite',
                'oracle', 'sql server', 'cassandra', 'dynamodb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes',
                'terraform', 'jenkins', 'gitlab', 'github actions'
            ],
            'tools': [
                'git', 'jira', 'confluence', 'slack', 'figma', 'sketch', 'photoshop',
                'illustrator', 'tableau', 'power bi', 'excel', 'powerpoint'
            ]
        }
        
        # Common soft skills
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving', 'analytical',
            'creative', 'detail oriented', 'organized', 'time management', 'adaptable',
            'collaborative', 'innovative', 'strategic thinking', 'customer focused'
        ]
        
        # Stop words to ignore
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 50) -> List[str]:
        """Extract relevant keywords from job description text"""
        if not text:
            return []
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Extract different types of keywords
        technical_keywords = self._extract_technical_skills(cleaned_text)
        soft_keywords = self._extract_soft_skills(cleaned_text)
        domain_keywords = self._extract_domain_keywords(cleaned_text)
        requirement_keywords = self._extract_requirement_keywords(cleaned_text)
        
        # Combine all keywords
        all_keywords = []
        all_keywords.extend(technical_keywords)
        all_keywords.extend(soft_keywords)
        all_keywords.extend(domain_keywords)
        all_keywords.extend(requirement_keywords)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in all_keywords:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        return unique_keywords[:max_keywords]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for processing"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important ones
        text = re.sub(r'[^\w\s\-\+\#\.\(\)]', ' ', text)
        
        return text.strip()
    
    def _extract_technical_skills(self, text: str) -> List[str]:
        """Extract technical skills and technologies"""
        found_skills = []
        
        for category, skills in self.technical_skills.items():
            for skill in skills:
                # Look for exact matches and variations
                patterns = [
                    rf'\b{re.escape(skill)}\b',
                    rf'\b{re.escape(skill)}\.js\b',  # For JavaScript frameworks
                    rf'\b{re.escape(skill)}\+\+\b',  # For C++
                    rf'\b{re.escape(skill)}#\b'      # For C#
                ]
                
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Capitalize properly
                        if skill in ['javascript', 'typescript']:
                            found_skills.append(skill.capitalize())
                        elif skill == 'c++':
                            found_skills.append('C++')
                        elif skill == 'c#':
                            found_skills.append('C#')
                        elif skill in ['aws', 'gcp', 'sql', 'api', 'ui', 'ux']:
                            found_skills.append(skill.upper())
                        else:
                            found_skills.append(skill.title())
                        break
        
        return found_skills
    
    def _extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills and personal qualities"""
        found_skills = []
        
        for skill in self.soft_skills:
            if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE):
                found_skills.append(skill.title())
        
        return found_skills
    
    def _extract_domain_keywords(self, text: str) -> List[str]:
        """Extract domain-specific keywords and industry terms"""
        domain_keywords = []
        
        # Common business/industry terms
        business_terms = [
            'agile', 'scrum', 'kanban', 'devops', 'ci/cd', 'microservices',
            'api', 'rest', 'graphql', 'machine learning', 'artificial intelligence',
            'data science', 'big data', 'analytics', 'business intelligence',
            'cybersecurity', 'blockchain', 'iot', 'mobile development',
            'web development', 'full stack', 'frontend', 'backend', 'ui/ux'
        ]
        
        for term in business_terms:
            if re.search(rf'\b{re.escape(term)}\b', text, re.IGNORECASE):
                # Proper capitalization
                if term in ['api', 'rest', 'ci/cd', 'iot']:
                    domain_keywords.append(term.upper())
                elif term == 'ui/ux':
                    domain_keywords.append('UI/UX')
                else:
                    domain_keywords.append(term.title())
        
        return domain_keywords
    
    def _extract_requirement_keywords(self, text: str) -> List[str]:
        """Extract keywords from requirement sections"""
        requirement_keywords = []
        
        # Look for years of experience patterns
        experience_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\+?\s*years?\s+(?:in|with)',
            r'minimum\s+(\d+)\s+years?',
            r'at least\s+(\d+)\s+years?'
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                requirement_keywords.append(f"{match}+ years experience")
        
        # Look for degree requirements
        degree_patterns = [
            r'\b(bachelor\'?s?|master\'?s?|phd|doctorate)\s+(?:degree\s+)?(?:in\s+)?(\w+)',
            r'\b(bs|ms|ba|ma)\s+(?:in\s+)?(\w+)',
            r'\b(computer science|engineering|mathematics|statistics)\b'
        ]
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    degree_text = ' '.join(match).strip()
                else:
                    degree_text = match
                if degree_text:
                    requirement_keywords.append(degree_text.title())
        
        # Look for certification keywords
        cert_keywords = [
            'certification', 'certified', 'license', 'licensed', 'aws certified',
            'microsoft certified', 'google certified', 'cisco certified',
            'pmp', 'cissp', 'cisa', 'cism'
        ]
        
        for keyword in cert_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
                requirement_keywords.append(keyword.title())
        
        return requirement_keywords
    
    def extract_skills_by_category(self, text: str) -> Dict[str, List[str]]:
        """Extract skills organized by category"""
        cleaned_text = self._clean_text(text)
        
        return {
            'technical_skills': self._extract_technical_skills(cleaned_text),
            'soft_skills': self._extract_soft_skills(cleaned_text),
            'domain_keywords': self._extract_domain_keywords(cleaned_text),
            'requirements': self._extract_requirement_keywords(cleaned_text)
        }
    
    def get_keyword_frequency(self, text: str) -> Dict[str, int]:
        """Get frequency count of keywords in text"""
        keywords = self.extract_keywords(text)
        cleaned_text = self._clean_text(text)
        
        frequency = {}
        for keyword in keywords:
            count = len(re.findall(rf'\b{re.escape(keyword)}\b', cleaned_text, re.IGNORECASE))
            frequency[keyword] = count
        
        return frequency
