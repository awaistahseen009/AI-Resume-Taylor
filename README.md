# Resume Tailor - AI-Powered Resume Optimization

A comprehensive web application that uses AI to tailor resumes for specific job descriptions, generate professional PDFs, and create personalized outreach messages.

## 🚀 Features

### Core Functionality

- **AI Resume Tailoring**: Automatically optimize resumes to match job descriptions using OpenAI GPT
- **Multi-Format Support**: Upload resumes in PDF, DOCX, or plain text
- **Professional PDF Generation**: Export beautiful resumes using LaTeX templates
- **Job Description Analysis**: Extract keywords and requirements from job postings
- **LaTeX Resume Generation**: Professional resume templates with LaTeX compilation
- **PDF Export**: Generate and download tailored resumes as PDFs
- **Resume Editor**: Side-by-side comparison of original and tailored resumes
- **Job Scraping**: Fetch related job postings from job boards
- **Vector Embeddings**: Store and search resumes using semantic similarity
- **Profile Dashboard**: Comprehensive user statistics and account management

## Technology Stack

- **Backend**: Flask (Python web framework)
- **AI/ML**: LangGraph, LangChain, OpenAI GPT
- **Vector Database**: Pinecone for semantic search and embeddings
- **Main Database**: Supabase (PostgreSQL) for synchronous operations
- **Authentication**: Flask-Login with bcrypt password hashing
- **Frontend**: Jinja2 templates with TailwindCSS
- **Document Processing**: PyPDF2, pdfplumber, python-docx
- **PDF Generation**: LaTeX (pdflatex/xelatex) with wkhtmltopdf fallback
- **Job Scraping**: BeautifulSoup4, requests
- **Embeddings**: Sentence Transformers for text vectorization

## 📋 Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Supabase account and project
- Pinecone account and API key
- LaTeX distribution (TeX Live, MiKTeX, or MacTeX) - optional but recommended
- Git

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/resume-tailor.git
cd resume-tailor
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Supabase Setup

1. Create a new project in [Supabase](https://supabase.com)
2. Go to Settings > API to get your project URL and API keys
3. In the SQL editor, run the commands from `create_tables.sql` to set up the database schema

#### Pinecone Setup

1. Create an account at [Pinecone](https://pinecone.io)
2. Create a new index with:
   - Dimension: 786 (google embedding models)
   - Metric: cosine
   - Name: resume-tailor-embeddings (or your preferred name)

### 5. Environment Setup

Create a `.env` file in the root directory:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True

# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
PINECONE_INDEX_NAME=resume-tailor-embeddings

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
# TAVILY_API_KEY= your-tavily-api-key
# File Upload Configuration
MAX_CONTENT_LENGTH=16777216  # 16MB in bytes
UPLOAD_FOLDER=uploads

# Security Configuration
WTF_CSRF_ENABLED=True

# LaTeX Configuration (optional)
LATEX_COMPILER=pdflatex  # or xelatex, lualatex

# Vector Database Configuration
EMBEDDING_MODEL=model/embedding-001
VECTOR_DIMENSION=384
```

### 6. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 Usage

### 1. Register/Login

- Create a new account or log in with existing credentials
- Access the dashboard to manage your resumes and job applications

### 2. Upload Resume

- Upload your resume in PDF, DOCX, or TXT format
- Or paste your resume text directly into the text area
- Add a descriptive title for easy identification
- Resume content is automatically vectorized and stored in Pinecone

### 3. Add Job Description

- Paste the job description you're targeting
- The system will analyze requirements and keywords
- Job descriptions are stored in Supabase and vectorized for semantic search
- Save job descriptions for future reference

### 4. Tailor Resume

- Select a resume and job description to tailor
- The AI will customize your resume to match the job requirements
- Review the side-by-side comparison in the editor
- Tailored versions are stored with updated vector embeddings

### 5. Generate PDF

- Download your tailored resume as a professional PDF
- Choose from multiple LaTeX templates
- Print-ready format suitable for applications

### 6. Profile Management

- View comprehensive statistics about your resumes and jobs
- Monitor vector database usage and search quality
- Manage account settings and preferences

### Editor Interface

- **Preview Resume**: Preview the tailored Resume
- **Download Resume PDF**: Download your tailored Resume
- **Cover Letters**: Generate cover letters
- **Similar Job skills search using tavily**: Use web base search to recommend the skills
- **Customized Profie**: Keep track of everything.

## 🏗 Project Structure

```
resume-tailor/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── README.md             # This file
│
├── routes/               # Flask blueprints
│   ├── __init__.py
│   ├── auth.py          # Authentication routes
│   ├── resume.py        # Resume management
│   ├── jobs.py          # Job description handling
│   └── messages.py      # Outreach message generation
│
├── services/            # Core business logic
│   ├── __init__.py
│   ├── ai_workflow.py   # LangGraph AI workflow
│   ├── resume_processor.py  # File processing
│   ├── latex_generator.py   # LaTeX template generation
│   ├── pdf_generator.py     # PDF compilation
│   ├── job_scraper.py       # Job posting scraping
│   ├── keyword_extractor.py # Keyword analysis
│   └── message_generator.py # Outreach message creation
│
├── templates/           # Jinja2 HTML templates
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Landing page
│   ├── dashboard.html  # Main user dashboard
│   ├── editor.html     # Resume editor interface
│   ├── auth/           # Authentication templates
│   │   ├── login.html
│   │   └── register.html
│   └── resume/         # Resume management templates
│       └── upload.html
│
├── static/             # Static assets (created at runtime)
│   ├── css/
│   ├── js/
│   └── images/
│
└── uploads/            # User uploaded files (created at runtime)
```

## 🔄 AI Workflow

The application uses LangGraph to orchestrate a sophisticated AI workflow:

1. **Resume Extraction**: Parse uploaded resume files
2. **Job Analysis**: Extract keywords and requirements from job descriptions
3. **Keyword Matching**: Identify relevant skills and experience
4. **Content Tailoring**: Rewrite resume content to match job requirements
5. **LaTeX Generation**: Create professional resume formatting
6. **Message Creation**: Generate personalized outreach content

## 🎨 UI/UX Design

### Theme

- **Dark Mode**: Professional black background with elegant contrasts
- **Accent Colors**: Gold (#FFD700) and Electric Blue (#00BFFF)
- **Typography**: Inter font family for modern readability
- **Animations**: Smooth transitions and hover effects

### Components

- **Glass Effect**: Translucent cards with backdrop blur
- **Gradient Text**: Eye-catching headers and highlights
- **Responsive Grid**: Adaptive layouts for all screen sizes
- **Interactive Elements**: Hover states and loading animations

## 🔐 Security Features

- **Password Hashing**: Bcrypt for secure password storage
- **Session Management**: Flask-Login for user sessions
- **File Validation**: Type and size checking for uploads
- **CSRF Protection**: Cross-site request forgery prevention
- **Input Sanitization**: XSS protection for user content

## 📊 Database Schema

### Users

- User authentication and profile information
- Relationships to resumes, jobs, and messages

### Resumes

- Original and tailored resume content
- LaTeX source and metadata
- File upload information

### Job Descriptions

- Target job postings and requirements
- Extracted keywords and analysis
- Related job suggestions

### Outreach Messages

- Generated emails, LinkedIn messages, and pitches
- Message type and tone preferences
- Associated job and resume references

## 🚀 Deployment

### Production Setup

1. **Environment Variables**:

   ```env
   FLASK_ENV=production
   SECRET_KEY=strong-production-key
   DATABASE_URL=postgresql://user:pass@host/db
   OPENAI_API_KEY=your-production-key
   ```

2. **Database Migration**:

   ```bash
   # For PostgreSQL
   pip install psycopg2-binary
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

3. **Web Server**: Use Gunicorn or similar WSGI server
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🧪 Testing

### Manual Testing

1. Test user registration and login
2. Upload different resume formats
3. Tailor resumes with various job descriptions
4. Generate and download PDFs
5. Create outreach messages

### Automated Testing

```bash
# Install testing dependencies
pip install pytest pytest-flask

# Run tests
pytest tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**Issue**: PDF generation fails
**Solution**: Install LaTeX distribution or ensure wkhtmltopdf is available

**Issue**: AI tailoring not working
**Solution**: Check OpenAI API key and account credits

**Issue**: File upload errors
**Solution**: Verify file format (PDF, DOCX, TXT) and size (<16MB)

### Getting Help

- Check the [Issues](https://github.com/your-repo/issues) page
- Review the documentation above
- Contact support at support@resumetailor.com

## 🔮 Future Enhancements

- **Multi-language Support**: Internationalization for global users
- **Advanced Analytics**: Resume performance tracking and insights
- **Integration APIs**: Connect with job boards and ATS systems
- **Team Collaboration**: Shared workspaces for career counselors
- **Mobile App**: Native iOS and Android applications
- **AI Improvements**: Enhanced natural language processing
- **Template Library**: Multiple resume design options

## 📈 Performance

- **Response Time**: <2 seconds for resume tailoring
- **File Processing**: Supports files up to 16MB
- **Concurrent Users**: Optimized for 100+ simultaneous users
- **Database**: Efficient indexing for fast queries
- **Caching**: Redis integration for improved performance

---

**Resume Tailor** - Empowering job seekers with AI-driven resume optimization. 🚀

Made with ❤️ using Python, Flask, and OpenAI GPT.
