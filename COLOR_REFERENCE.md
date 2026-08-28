# Color Reference

## Primary Gradient Orange

- **Start:** `#FF6B35` (Vibrant Orange)
- **End:** `#B03A14` (Dark Orange)
- **Usage:** Header background, login page, message header, buttons
- **Gradient:** `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`

## Accent Orange Gradient (Message Bubbles)

- **Start:** `#FF6B35` (Vibrant Orange)
- **End:** `#E85A2A` (Orange)
- **Usage:** Client message bubbles, avatar gradients
- **Gradient:** `linear-gradient(135deg, #FF6B35 0%, #E85A2A 100%)`

## Orange Accent (CTA Buttons)

- **Primary:** `#FF9933` (Orange-400)
- **Secondary:** `#FF6B35` (Orange-500)
- **Dark:** `#E85A2A` (Orange-600)
- **Darker:** `#CC4A1F` (Orange-700)
- **Gradient:** `linear-gradient(135deg, #FF6B35 0%, #E85A2A 100%)`
- **Hover Gradient:** `linear-gradient(135deg, #E85A2A 0%, #CC4A1F 100%)`
- **Usage:** Primary action buttons, highlights

## Neutral Colors

- **White:** `#FFFFFF`, `#fff`
- **Gray-50:** `#f8f9fa`, `#f8fafc`
- **Gray-100:** `#e9ecef`, `#f1f5f9`
- **Gray-200:** `#dee2e6`, `#e2e8f0`
- **Gray-300:** `#ced4da`
- **Gray-400:** `#adb5bd`, `#94a3b8`
- **Gray-500:** `#6c757d`, `#64748b`
- **Gray-600:** `#495057`, `#475569`
- **Gray-700:** `#343a40`, `#334155`
- **Gray-800:** `#212529`, `#1e293b`
- **Gray-900:** `#0f172a`

## Status Colors

- **Success:** `#22c55e`, `#16a34a`, `#047857`
- **Danger:** `#dc2626`, `#ef4444`
- **Warning:** `#f97316`, `#f59e0b`
- **Info:** `#3b82f6`, `#0d6efd`

## CSS Variables (layout.html)

```css
--accent-50: #fff0e6 --accent-100: #ffe0cc --accent-200: #ffcc99
  --accent-300: #ffb366 --accent-400: #ff9933 --accent-500: #ff6b35
  --accent-600: #e85a2a --accent-700: #cc4a1f --accent-800: #b03a14
  --accent-900: #942a09 --header-color: #ff6b35 --yellow-400: #ff9933
  --yellow-500: #ff6b35 --yellow-600: #e85a2a;
```

## Page-Specific Colors

### Header (header.html)

- Background: `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`

### Login Page (auth/login.html)

- Background: `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`
- Header: `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`

### Client Support (client/support.html)

- Message Header: `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`
- Client Message Bubble: `linear-gradient(135deg, #FF6B35 0%, #E85A2A 100%)`

### Change Password (account/change_password.html)

- Hero: `linear-gradient(135deg, #1f2937 0%, #FF6B35 100%)`
- Submit Button: `linear-gradient(135deg, #FF6B35, #E85A2A)`

### Admin Messages (admin/messages.html)

- Active Conversation: `rgba(255,107,53,.08)` with `#FF6B35` border
- Send Button: `#FF6B35`

### Survey Error (survey_error.html)

- Background: `linear-gradient(135deg, #FF6B35 0%, #B03A14 100%)`
- Icon: `#FF6B35`
