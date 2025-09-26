# 🤖 AI Email Campaign Manager - Production Ready

A professional email marketing platform with AI-powered automation, optimized for Vercel deployment.

## ✅ **PRODUCTION OPTIMIZED**

- **🚀 Vercel Ready** - Optimized for Vercel deployment
- **⚡ Production Code** - Removed all demo/test content
- **📦 Clean Dependencies** - Minimal production dependencies
- **🔧 Auto-Deploy** - Ready for Vercel deployment
- **🤖 AI Automation** - Full AI email reply system

## 🚀 **Deployment Options**

### **Option 1: Vercel Deployment (Recommended)**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel

# Set environment variables in Vercel dashboard:
# - EMAIL: your-gmail@gmail.com
# - PASSWORD: your-app-password
# - GEMINI_API_KEY: your-gemini-api-key
```

### **Option 2: Local Development**
```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the application
python3 app.py

# Open: http://localhost:5008
```

### **Environment Variables**
Set these in Vercel dashboard:
- `EMAIL`: Your Gmail address
- `PASSWORD`: Your Gmail app password
- `GEMINI_API_KEY`: Your Gemini API key

## 🎯 **Features**

- **📧 Contact Management** - Add, remove, and manage contacts
- **📬 Email Campaigns** - Send personalized email campaigns
- **🤖 AI-Powered Replies** - Automatic responses using Gemini AI
- **📊 Analytics Dashboard** - Real-time statistics and monitoring
- **⚡ Fast & Reliable** - Optimized for local performance

## 🔧 **API Endpoints**

### Contact Management
- `GET /get-contacts` - Get all contacts
- `GET /api/contacts` - Get all contacts (API version)
- `POST /add-contact` - Add a single contact
- `POST /api/add-contact` - Add a single contact (API version)
- `POST /remove-contact` - Remove a contact

### Campaign Management
- `POST /start-manual-campaign` - Start email campaign
- `POST /reset-campaign` - Reset campaign status
- `GET /api/status` - Get campaign status

### Analytics
- `GET /api/analytics` - Get comprehensive analytics
- `GET /api/dashboard-stats` - Get dashboard statistics

### AI Features
- `POST /api/send-ai-reply` - Send AI-generated reply

## 📁 **Project Structure**

```
automated-email-sender/
├── app.py                    # Main Flask application (CLEAN)
├── templates/
│   └── unified_dashboard.html
├── requirements.txt          # Minimal dependencies
├── README.md                # This file
└── LICENSE                  # MIT License
```

## 🛠️ **Configuration**

The application uses these default settings:
- **Email**: karmaterra427@gmail.com
- **SMTP**: Gmail SMTP (smtp.gmail.com:587)
- **AI**: Gemini 2.0 Flash API
- **Port**: 5008

## 🧪 **Testing**

The application includes all necessary endpoints and is ready to use immediately after installation.

## 📊 **Analytics Dashboard**

The dashboard provides:
- Total contacts count
- Emails sent counter
- Success rate percentage
- Campaign status
- AI reply statistics

## 🤖 **AI Features**

- **Automatic Reply Generation**: Uses Gemini AI to generate professional responses
- **Smart Email Analysis**: Analyzes incoming emails for context
- **Personalized Responses**: Tailors replies based on sender and content

## 🔍 **Troubleshooting**

If you encounter any issues:
1. Make sure Python 3.9+ is installed
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `python app.py`
4. Check that port 5008 is available

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for local development and production use!**

*"Simple, clean, and powerful email marketing automation!"* 🚀