# VM Copy Question Generator - Next.js

A Next.js web application that uses OpenAI GPT models to generate copy questions based on a base question. The application is designed for educators to create multiple variations of mathematical questions aligned with US curricula standards.

## Features

- **Base Question Input**: Enter a base question that serves as the template
- **Smart Question Generation**: 
  - Mathematical questions: Same phrasing with different numbers
  - Word problems: Different real-life context while maintaining mathematical structure
  - Image-based questions: Generate questions with visual elements
- **Curriculum Alignment**: Questions are aligned with US curricula standards and grade levels
- **Customizable Options**: 
  - Number of options (auto-detected or manual)
  - Number of copy questions to generate
  - Difficulty level (Easy, Medium, Hard)
- **Image Support**: Upload images or provide image URLs
- **Notes Field**: Add context-specific notes for question generation
- **Copy Functionality**: Copy individual questions or all questions at once

## Setup Instructions

### Prerequisites

- Node.js 18+ and npm
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd vm-copy-question-generator
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. Run the development server:
```bash
npm run dev
```

5. Open your browser and navigate to:
```
http://localhost:3000
```

## Project Structure

```
vm-copy-question-generator/
├── app/
│   ├── api/
│   │   ├── generate/
│   │   │   └── route.ts          # API route for question generation
│   │   └── verify/
│   │       └── route.ts          # API route for question verification
│   ├── generate/
│   │   └── page.tsx              # Question generator page
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Home page
│   └── globals.css               # Global styles
├── lib/
│   ├── openai.ts                 # OpenAI client utilities
│   ├── curriculum.ts             # Curriculum data utilities
│   ├── question-utils.ts         # Question generation utilities
│   └── subskills.ts              # Subskills data
├── public/
│   └── static/
│       └── images/               # Static images
├── package.json
├── tsconfig.json
└── next.config.js
```

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Go to [Vercel](https://vercel.com) and sign up/login
3. Click "New Project" and import your repository
4. Add environment variable: `OPENAI_API_KEY`
5. Deploy!

### Other Platforms

- **Netlify**: Similar to Vercel, supports Next.js out of the box
- **Railway**: Supports Next.js with automatic deployments
- **Render**: Can deploy Next.js applications

## Environment Variables

- `NARAROUTER_API_KEY`: Your NaraRouter API key (required if using NaraRouter models like `agnes-3-flash`)
- `NARAROUTER_BASE_URL`: NaraRouter API Base URL (defaults to `https://router.bynara.id/v1`)
- `OPENAI_API_KEY`: Your OpenAI API key (optional if using NaraRouter)
- `GEMINI_API_KEY`: Your Google Gemini API key (optional if using NaraRouter)

## Notes

- The application uses OpenAI GPT models (gpt-4o, gpt-5, o3, o4-mini) for question generation
- Ensure you have sufficient OpenAI API credits
- Generated questions include option logic (CA for correct answer, Plausible distractors with explanations)
- Supports three question types: Mathematical, Word Problems, and Image-based questions
- Includes verification feature to check question correctness
- Curriculum data supports Common Core, TEKS, VA SOL, FL BEST, and CA CCSS

## License

This project is for educational purposes.

