# Career Roadmap Backend API

This document describes the backend endpoints currently available to the frontend.

## Local setup

- Base URL: http://localhost:5000
- Requests and responses use JSON.
- For POST requests, send Content-Type: application/json.
- Start from this project folder with npm.cmd start in Windows PowerShell.

> Demo limitation: Career roles and roadmap steps are temporary sample data, not verified live industry data and not AI-generated. Profiles are stored in server memory only and disappear when the server restarts. MongoDB and authentication are not currently used by these routes.

## Endpoints

### 1. Health check

GET /api/health — no request body.

Example response (200 OK):

```json
{
  "status": "ok",
  "message": "AI Career Roadmap API is running smoothly",
  "timestamp": "2026-10-24T17:15:20.591Z"
}
```

### 2. List career roles

GET /api/roles — no request body. Current sample role IDs are role-1, role-2, and role-3.

Example response (200 OK; abbreviated to one role):

```json
{
  "success": true,
  "message": "Temporary sample career roles (mock data for development)",
  "totalRoles": 3,
  "roles": [
    {
      "id": "role-1",
      "title": "Full-Stack Web Developer",
      "category": "Software Development",
      "description": "Builds both user-facing frontends and backend servers/APIs for modern web applications.",
      "requiredSkills": ["JavaScript", "HTML & CSS", "React", "Node.js", "Express.js", "MongoDB", "Git & GitHub"]
    }
  ]
}
```

The real response includes all three sample roles.

### 3. Analyze skills for a role

POST /api/skill-gap

Request body:

```json
{
  "roleId": "role-1",
  "skills": ["JavaScript", "React", "Node.js"]
}
```

Example response (200 OK):

```json
{
  "success": true,
  "roleId": "role-1",
  "roleTitle": "Full-Stack Web Developer",
  "analysis": {
    "totalRequiredSkills": 7,
    "matchedCount": 3,
    "missingCount": 4,
    "matchPercentage": "43%",
    "explanation": "You have 3 of 7 required skills (43% match). Missing 4 skill(s) to reach 100%."
  },
  "matchedSkills": ["JavaScript", "React", "Node.js"],
  "missingSkills": ["HTML & CSS", "Express.js", "MongoDB", "Git & GitHub"]
}
```

Possible errors: 400 if roleId or skills is invalid; 404 if the role ID does not exist.

### 4. Create a temporary student profile

POST /api/profiles

Request body:

```json
{
  "name": "Demo Student",
  "education": "B.Tech CSE",
  "skills": ["JavaScript", "React"],
  "targetRoleId": "role-1"
}
```

Example response (201 Created, abbreviated):

```json
{
  "success": true,
  "message": "Student profile created successfully (temporary in-memory storage)",
  "profile": {
    "id": "<generated-uuid>",
    "name": "Demo Student",
    "education": "B.Tech CSE",
    "skills": ["JavaScript", "React"],
    "targetRoleId": "role-1",
    "targetRoleTitle": "Full-Stack Web Developer",
    "createdAt": "<ISO-8601 timestamp>"
  }
}
```

Save profile.id from the response and use it in the profile endpoints below. Possible errors: 400 for invalid fields or an unknown role ID.

### 5. Get a student profile

GET /api/profiles/:id — replace :id with the UUID returned by profile creation. No request body.

Example response (200 OK):

```json
{
  "success": true,
  "profile": {
    "id": "<profile-id>",
    "name": "Demo Student",
    "education": "B.Tech CSE",
    "skills": ["JavaScript", "React"],
    "targetRoleId": "role-1",
    "targetRoleTitle": "Full-Stack Web Developer",
    "createdAt": "<ISO-8601 timestamp>"
  }
}
```

Returns 404 if the profile is not found.

### 6. Get the saved profile skill gap

GET /api/profiles/:id/skill-gap — no request body. Uses the saved profile skills and target role.

Example response (200 OK, abbreviated):

```json
{
  "success": true,
  "profileId": "<profile-id>",
  "studentName": "Demo Student",
  "roleId": "role-1",
  "roleTitle": "Full-Stack Web Developer",
  "analysis": {
    "totalRequiredSkills": 7,
    "matchedCount": 2,
    "missingCount": 5,
    "matchPercentage": "29%",
    "explanation": "You have 2 of 7 required skills (29% match). Missing 5 skill(s) to reach 100%."
  },
  "matchedSkills": ["JavaScript", "React"],
  "missingSkills": ["HTML & CSS", "Node.js", "Express.js", "MongoDB", "Git & GitHub"]
}
```

Returns 404 if the profile or its role is not found.

### 7. Get a demo roadmap for a saved profile

GET /api/profiles/:id/roadmap — no request body. Creates ordered learning steps for skills missing from that profile.

Example response (200 OK, abbreviated to one step):

```json
{
  "success": true,
  "profileId": "<profile-id>",
  "studentName": "Demo Student",
  "targetRoleId": "role-1",
  "targetRoleTitle": "Full-Stack Web Developer",
  "notice": "Temporary demo roadmap for development purposes. Not live industry data or AI-generated.",
  "summary": {
    "totalRequiredSkills": 7,
    "acquiredSkillsCount": 2,
    "missingSkillsCount": 5,
    "totalRoadmapSteps": 5
  },
  "roadmap": [
    {
      "stepNumber": 1,
      "skill": "HTML & CSS",
      "learningGoal": "Master semantic HTML markup, responsive web design with Flexbox and CSS Grid.",
      "practiceTask": "Build a responsive multi-page personal portfolio site from scratch without frameworks.",
      "estimatedDuration": "1-2 weeks"
    }
  ]
}
```

The actual response has one step per missing skill. Returns 404 if the profile or its role is not found.

## Frontend integration notes

- During local development, call the API at http://localhost:5000.
- Send JSON request bodies for POST routes and parse the JSON responses.
- Keep the UUID returned by POST /api/profiles for the profile detail, skill-gap, and roadmap routes.
- These endpoints currently have no login/authentication and do not persist profiles in MongoDB.
