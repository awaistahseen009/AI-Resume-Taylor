import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus, urljoin
import json

class JobScraper:
    """Service for scraping job postings from various sources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_jobs(self, job_title: str, location: str = "", max_results: int = 10) -> List[Dict[str, str]]:
        """Search for jobs from multiple sources"""
        all_jobs = []
        
        # Try different job sources
        try:
            indeed_jobs = self._search_indeed(job_title, location, max_results // 2)
            all_jobs.extend(indeed_jobs)
        except Exception as e:
            print(f"Indeed search failed: {e}")
        
        try:
            # Add other job sources here
            pass
        except Exception as e:
            print(f"Other job source failed: {e}")
        
        # If no jobs found from scraping, return mock data for demo
        if not all_jobs:
            all_jobs = self._generate_mock_jobs(job_title, location, max_results)
        
        return all_jobs[:max_results]
    
    def _search_indeed(self, job_title: str, location: str, max_results: int) -> List[Dict[str, str]]:
        """Search Indeed for job postings"""
        jobs = []
        
        # Construct Indeed search URL
        base_url = "https://www.indeed.com/jobs"
        params = {
            'q': job_title,
            'l': location,
            'limit': min(max_results, 50)
        }
        
        try:
            response = self.session.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job cards (Indeed's structure may change)
            job_cards = soup.find_all(['div'], class_=re.compile(r'job_seen_beacon|result|jobsearch-SerpJobCard'))
            
            for card in job_cards[:max_results]:
                try:
                    job = self._parse_indeed_job_card(card)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"Indeed scraping error: {e}")
        
        return jobs
    
    def _parse_indeed_job_card(self, card) -> Optional[Dict[str, str]]:
        """Parse individual Indeed job card"""
        try:
            job = {}
            
            # Extract job title
            title_elem = card.find(['h2', 'a'], class_=re.compile(r'jobTitle'))
            if title_elem:
                job['title'] = title_elem.get_text(strip=True)
                # Extract job URL
                link = title_elem.find('a')
                if link and link.get('href'):
                    job['url'] = urljoin('https://www.indeed.com', link['href'])
            
            # Extract company name
            company_elem = card.find(['span', 'a'], class_=re.compile(r'companyName'))
            if company_elem:
                job['company'] = company_elem.get_text(strip=True)
            
            # Extract location
            location_elem = card.find(['div'], class_=re.compile(r'companyLocation'))
            if location_elem:
                job['location'] = location_elem.get_text(strip=True)
            
            # Extract job snippet/description
            snippet_elem = card.find(['div'], class_=re.compile(r'job-snippet'))
            if snippet_elem:
                job['description_snippet'] = snippet_elem.get_text(strip=True)
            
            # Extract salary if available
            salary_elem = card.find(['span'], class_=re.compile(r'salary'))
            if salary_elem:
                job['salary'] = salary_elem.get_text(strip=True)
            
            job['source'] = 'Indeed'
            
            return job if job.get('title') and job.get('company') else None
            
        except Exception as e:
            return None
    
    def _generate_mock_jobs(self, job_title: str, location: str, count: int) -> List[Dict[str, str]]:
        """Generate mock job data for demonstration purposes"""
        companies = [
            "TechCorp Inc", "Innovation Labs", "Digital Solutions", "Future Systems",
            "DataTech", "CloudWorks", "NextGen Software", "Smart Analytics",
            "AI Dynamics", "Cyber Solutions"
        ]
        
        locations = [
            "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
            "Boston, MA", "Chicago, IL", "Los Angeles, CA", "Denver, CO"
        ]
        
        job_descriptions = [
            f"We are seeking a talented {job_title} to join our dynamic team. The ideal candidate will have strong technical skills and experience with modern technologies.",
            f"Exciting opportunity for a {job_title} to work on cutting-edge projects. We offer competitive compensation and excellent benefits.",
            f"Join our innovative team as a {job_title}. You'll work with the latest technologies and contribute to impactful projects.",
            f"We're looking for an experienced {job_title} to help drive our technology initiatives forward.",
            f"Great opportunity for a {job_title} to grow their career in a fast-paced, collaborative environment."
        ]
        
        jobs = []
        for i in range(count):
            job = {
                'title': job_title,
                'company': companies[i % len(companies)],
                'location': location if location else locations[i % len(locations)],
                'description_snippet': job_descriptions[i % len(job_descriptions)],
                'url': f"https://example-job-site.com/job/{i+1}",
                'source': 'Demo Data',
                'salary': f"${60000 + (i * 5000)} - ${80000 + (i * 5000)}" if i % 3 == 0 else None
            }
            jobs.append(job)
        
        return jobs
    
    def get_job_details(self, job_url: str) -> Optional[Dict[str, str]]:
        """Fetch detailed job description from job URL"""
        try:
            response = self.session.get(job_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to extract full job description
            # This is a generic approach - would need customization per site
            description_selectors = [
                'div[class*="jobDescription"]',
                'div[class*="job-description"]',
                'div[id*="jobDescription"]',
                '.job-description',
                '.description'
            ]
            
            description = ""
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break
            
            return {
                'full_description': description,
                'url': job_url
            }
            
        except Exception as e:
            print(f"Error fetching job details: {e}")
            return None
