# Applicant Screening and Interview Validation System

This project implements an Applicant Screening and Interview Validation System, designed to streamline the hiring process by utilizing a decision engine powered by machine learning and natural language processing.

## Project Structure

- **src/**: Contains the main application code.
  - **app.py**: Entry point of the application.
  - **mcp_servers/**: Contains the logic for the MCP Decision Engine.
    - **decision_engine.py**: Scoring, validation, and recommendation functions.
    - **applicant_analyzer.py**: Analyzes applicant data and extracts features.
    - **interview_validator.py**: Validates interview data and assesses performance.
  - **agents/**: Contains agents that interact with the screening and validation processes.
    - **screening_agent.py**: Processes resumes and extracts information.
    - **validation_agent.py**: Manages interview validation and scoring.
  - **models/**: Defines data models for applicants and interviews.
    - **applicant.py**: Applicant model with properties like name and experience.
    - **interview.py**: Interview model with candidate responses and scores.
  - **utils/**: Utility functions for various tasks.
    - **llm_client.py**: Interacts with the Language Model client.
    - **config_loader.py**: Loads configuration settings from JSON files.
  - **tools/**: Implements specific functionalities.
    - **resume_parser.py**: Parses resumes and extracts relevant data.
    - **interview_scorer.py**: Scores interviews based on criteria.

- **config/**: Contains configuration files.
  - **mcp_servers.json**: Configuration for MCP servers.
  - **aicore_config.json**: Configuration for AI core services.

- **tests/**: Contains unit tests for the application.
  - **test_decision_engine.py**: Tests for the decision engine logic.
  - **test_agents.py**: Tests for the agents' functionality.

- **requirements.txt**: Lists project dependencies.

- **.env.example**: Example of environment variables needed for the project.

## Setup Instructions

1. Clone the repository.
2. Install the required dependencies using `pip install -r requirements.txt`.
3. Configure the environment variables as needed by copying `.env.example` to `.env` and updating the values.
4. Ensure that the MCP servers and AI core configurations are set in the `config` directory.
5. Run the application using `python src/app.py`.

## Usage Guidelines

- The system allows for the submission of applicant resumes and interview data.
- The decision engine processes this data to provide scoring and validation results.
- Agents facilitate the interaction between the user and the underlying logic.

## Overview of the Architecture

The architecture is designed to be modular, allowing for easy updates and maintenance. Each component has a specific responsibility, ensuring that the system is scalable and efficient. The use of MCP servers enables advanced decision-making capabilities, while the integration of AI core services enhances the overall functionality of the system.