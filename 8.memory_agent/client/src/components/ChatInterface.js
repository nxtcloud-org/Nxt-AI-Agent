import React, { useState, useRef, useEffect } from "react";
import config from "../config";
import "./ChatInterface.css";

const ChatInterface = ({ studentData }) => {
  const [messages, setMessages] = useState([
    {
      type: "system",
      content: `안녕하세요 ${studentData.name}님! 학사 상담 AI 에이전트입니다. 이전 대화를 기억하여 연속성 있는 상담을 제공합니다. 궁금한 것이 있으시면 언제든 물어보세요.`,
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [memoryStatus, setMemoryStatus] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // 메모리 상태 조회
    const fetchMemoryStatus = async () => {
      try {
        const response = await fetch(
          `${config.API_URL}/api/memory/${studentData.student_id}`
        );
        if (response.ok) {
          const data = await response.json();
          setMemoryStatus(data);
        }
      } catch (error) {
        console.error("Memory status fetch error:", error);
      }
    };

    fetchMemoryStatus();
  }, [studentData.student_id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      type: "user",
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      const response = await fetch(`${config.API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
          student_id: studentData.student_id,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const aiMessage = {
          type: "ai",
          content: data.response,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMessage]);

        // 메모리 상태 업데이트
        if (memoryStatus) {
          setMemoryStatus((prev) => ({
            ...prev,
            conversation_count: prev.conversation_count + 1,
          }));
        }
      } else {
        const error = await response.json();
        const errorMessage = {
          type: "error",
          content: error.message || "응답을 받는데 실패했습니다.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        type: "error",
        content: "서버 연결에 실패했습니다.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const suggestedQuestions = [
    "내 졸업 요건 알려줘",
    "다음 학기 추천해줘",
    "내 성적 분석해줘",
    "이전에 상담한 내용 요약해줘",
  ];

  const handleSuggestedQuestion = (question) => {
    setInputMessage(question);
  };

  return (
    <div className="chat-container">
      {memoryStatus && (
        <div className="memory-status">
          <div className="memory-info">
            <span className="memory-icon">🧠</span>
            <span className="memory-text">
              대화 기록 {memoryStatus.conversation_count}개
            </span>
            {memoryStatus.conversation_count > 0 && (
              <span className="memory-indicator">활성</span>
            )}
          </div>
        </div>
      )}
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            <div className="message-content">{message.content}</div>
            <div className="message-time">{formatTime(message.timestamp)}</div>
          </div>
        ))}
        {isLoading && (
          <div className="message ai loading">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              AI가 답변을 생성하고 있습니다...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="suggested-questions">
          <h3>💡 추천 질문</h3>
          <div className="question-buttons">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => handleSuggestedQuestion(question)}
                className="suggestion-btn"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-container">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="궁금한 것을 물어보세요..."
            disabled={isLoading}
            className="chat-input"
          />
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="send-btn"
          >
            {isLoading ? "⏳" : "📤"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
