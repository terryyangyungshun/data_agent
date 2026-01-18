import { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import { Send, Bot, User } from 'lucide-react';
import { API_ENDPOINTS } from '../config/api';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const initialMessages: Message[] = [
  {
    id: '1',
    type: 'assistant',
    content: '您好！我是資料分析助手，可以幫您分析上傳的資料集。請在右側上傳CSV檔案，然後選擇變數進行分析，我會為您提供詳細的分析結果和建議。',
    timestamp: new Date()
  }
];

interface ChatInterfaceProps {
  clearTrigger: number;
  onImageGenerated?: (imageUrl: string) => void;
}

export function ChatInterface({ clearTrigger, onImageGenerated }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // 監聽清除觸發器，重設對話
  useEffect(() => {
    if (clearTrigger > 0) {
      setMessages(initialMessages);
      setInputValue('');
      setIsLoading(false);
    }
  }, [clearTrigger]);

  // 建立訊息歷史（LangServe格式）
  const buildMessageHistory = () => {
    return messages
      .filter(msg => 
        msg.id !== '1' && // 排除初始歡迎訊息
        msg.content.trim() !== '' // 排除空訊息
      )
      .map(msg => ({
        type: msg.type === 'user' ? 'human' : 'ai',
        content: msg.content
      }));
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // 建立一個暫時的 assistant 訊息來顯示串流內容
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // 建立請求體（LangServe格式）
      const messageHistory = buildMessageHistory();
      const requestBody = {
        input: {
          messages: [
            ...messageHistory,
            { type: 'human', content: userMessage.content }
          ]
        }
      };

      console.log('🚀 發送請求:', JSON.stringify(requestBody, null, 2));

      const response = await fetch(API_ENDPOINTS.AGENT_STREAM, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('📡 回應狀態:', response.status, response.statusText);
      console.log('📋 回應標頭:', {
        contentType: response.headers.get('content-type'),
        transferEncoding: response.headers.get('transfer-encoding'),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      console.log('📖 Reader:', reader ? '已建立' : 'undefined');
      
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      let buffer = '';
      let chunkCount = 0;

      if (reader) {
        console.log('🔄 開始讀取串流...');
        while (true) {
          console.log(`📦 讀取第 ${chunkCount + 1} 個chunk...`);
          const { done, value } = await reader.read();
          console.log(`✅ 收到chunk ${chunkCount + 1}:`, { done, valueLength: value?.length });
          
          if (done) {
            console.log('🏁 串流讀取完成');
            break;
          }
          
          chunkCount++;

          // 將新資料加入緩衝區
          const decodedChunk = decoder.decode(value, { stream: true });
          console.log(`📝 解碼後的原始文字長度:`, decodedChunk.length);
          console.log(`📝 前300字元:`, decodedChunk.substring(0, 300));
          console.log(`📝 是否以\\n\\n結尾:`, decodedChunk.endsWith('\n\n'));
          buffer += decodedChunk;
          
          // SSE 格式：區塊之間用雙換行分隔
          const blocks = buffer.split('\n\n');
          console.log(`📚 分割出 ${blocks.length} 個區塊，buffer長度: ${buffer.length}`);
          
          // 只有當buffer不以\n\n結尾時，最後一個區塊才可能不完整
          // 否則所有區塊都是完整的（最後一個是空字串）
          if (!buffer.endsWith('\n\n')) {
            buffer = blocks.pop() || '';
            console.log(`⏳ 保留不完整的區塊到buffer，長度: ${buffer.length}`);
          } else {
            buffer = '';
            console.log(`✅ 所有區塊都完整`);
          }
          
          console.log(`🔢 準備處理 ${blocks.length} 個區塊`);

          for (const block of blocks) {
            if (!block.trim()) {
              console.log('⏭️  跳過空區塊');
              continue;
            }
            console.log(`🔍 處理區塊:`, block.substring(0, 100));

            const lines = block.split('\n');
            let eventType = '';
            let dataContent = '';

            // 解析每個區塊中的 event 和 data
            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                dataContent = line.slice(5).trim();
              }
            }

            console.log('SSE區塊 - 事件類型:', eventType);
            console.log('SSE區塊 - 原始資料:', dataContent);

            // 只處理 event: data 類型的訊息
            if (eventType === 'data' && dataContent) {
              try {
                const parsed = JSON.parse(dataContent);
                console.log('✅ 解析到的完整JSON:', parsed);
                console.log('📦 JSON結構的keys:', Object.keys(parsed));
                
                // 嘗試從不同可能的路徑提取 messages
                // LangServe SSE 串流的結構是 { model: { messages: [...] } }
                let messagesArray = parsed.model?.messages || parsed.messages || parsed.output?.messages;
                
                console.log('📨 提取到的messages陣列:', messagesArray);
                
                // 從 messages 陣列中提取最後一個訊息
                if (messagesArray && Array.isArray(messagesArray) && messagesArray.length > 0) {
                  const lastMessage = messagesArray[messagesArray.length - 1];
                  console.log('🔍 最後一條訊息:', lastMessage);
                  console.log('🔍 訊息類型:', lastMessage.type);
                  console.log('🔍 訊息內容:', lastMessage.content);
                  
                  // 如果有 content，顯示內容
                  if (lastMessage.content && typeof lastMessage.content === 'string' && lastMessage.content.trim()) {
                    accumulatedContent = lastMessage.content;
                    console.log('更新內容為:', accumulatedContent);
                    
                    // 偵測圖片產生標記
                    const imageMatch = accumulatedContent.match(/IMAGE_GENERATED:\s*(\S+)/);
                    if (imageMatch && onImageGenerated) {
                      const filename = imageMatch[1];
                      const imageUrl = `http://localhost:8002/static/images/${filename}`;
                      console.log('偵測到產生的圖片:', imageUrl);
                      onImageGenerated(imageUrl);
                    }
                    
                    // 更新訊息內容
                    setMessages(prev => prev.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, content: accumulatedContent }
                        : msg
                    ));
                  }
                  // 如果有 tool_calls，顯示"分析中..."
                  else if (lastMessage.tool_calls && lastMessage.tool_calls.length > 0) {
                    console.log('偵測到工具呼叫，顯示分析中...');
                    if (!accumulatedContent) {
                      setMessages(prev => prev.map(msg => 
                        msg.id === assistantMessageId 
                          ? { ...msg, content: '正在分析中...' }
                          : msg
                      ));
                    }
                  }
                  // 如果是工具訊息，可以顯示工具執行結果（可選）
                  else if (lastMessage.type === 'tool') {
                    console.log('工具執行完畢，結果:', lastMessage.content);
                  }
                }
              } catch (e) {
                console.error('解析SSE資料時發生錯誤:', e, '原始資料:', dataContent);
              }
            } else if (eventType === 'end') {
              console.log('串流結束');
              break;
            }
          }
        }
        
        // 🔥 關鍵修正：串流結束後處理剩餘的buffer
        console.log(`🔥 串流結束，處理剩餘buffer，長度: ${buffer.length}`);
        if (buffer.trim()) {
          console.log(`🔥 剩餘buffer內容（前500字元）:`, buffer.substring(0, 500));
          
          // 直接在整個buffer中尋找所有的 event: data 區塊
          const dataEventRegex = /event:\s*data\s*\n\s*data:\s*({[\s\S]*?})(?=\s*\n\s*event:|\s*$)/g;
          let match;
          let foundData = false;
          
          while ((match = dataEventRegex.exec(buffer)) !== null) {
            const dataContent = match[1];
            console.log('🔥 找到data事件，資料:', dataContent.substring(0, 200));
            foundData = true;
            
            try {
              const parsed = JSON.parse(dataContent);
              console.log('🔥 解析成功，keys:', Object.keys(parsed));
              const messagesArray = parsed.model?.messages || parsed.messages || parsed.output?.messages;
              
              if (messagesArray && Array.isArray(messagesArray) && messagesArray.length > 0) {
                const lastMessage = messagesArray[messagesArray.length - 1];
                console.log('🔥 最後一條訊息 type:', lastMessage.type);
                console.log('🔥 最後一條訊息 content:', lastMessage.content?.substring(0, 100));
                
                if (lastMessage.type === 'ai' && lastMessage.content && typeof lastMessage.content === 'string' && lastMessage.content.trim()) {
                  accumulatedContent = lastMessage.content;
                  console.log('✅✅✅ 找到AI回覆，更新介面！');
                  
                  const imageMatch = accumulatedContent.match(/IMAGE_GENERATED:\s*(\S+)/);
                  if (imageMatch && onImageGenerated) {
                    const filename = imageMatch[1];
                    const imageUrl = `http://localhost:8002/static/images/${filename}`;
                    console.log('偵測到產生的圖片:', imageUrl);
                    onImageGenerated(imageUrl);
                  }
                  
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessageId 
                      ? { ...msg, content: accumulatedContent }
                      : msg
                  ));
                }
              }
            } catch (e) {
              console.error('🔥 解析錯誤:', e);
            }
          }
          
          if (!foundData) {
            console.error('❌ 未找到任何 event: data 區塊');
          }
        }
        
        console.log(`✅ 總共讀取了 ${chunkCount} 個chunks`);
      } else {
        console.error('❌ 無法建立 reader - response.body 為空');
      }

      setIsLoading(false);
    } catch (error) {
      console.error('呼叫agent時發生錯誤:', error);
      
      // 顯示錯誤訊息
      setMessages(prev => prev.map(msg => 
        msg.id === assistantMessageId 
          ? { ...msg, content: '抱歉，呼叫AI助手時發生錯誤。請檢查後端服務是否正常執行。' }
          : msg
      ));
      
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full p-6 custom-scrollbar">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.type === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.type === 'assistant' && (
                <div className="w-8 h-8 bg-gradient-to-r from-amber-500/60 to-yellow-500/60 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-400/20 border border-amber-400/30">
                  <Bot className="w-4 h-4 text-amber-100" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] p-4 rounded-2xl whitespace-pre-wrap shadow-lg ${
                  message.type === 'user'
                    ? 'bg-gradient-to-r from-amber-600/80 to-orange-600/80 text-amber-50 ml-auto shadow-amber-400/20 border border-amber-400/30'
                    : 'bg-gray-900/85 backdrop-blur-md text-white border border-amber-400/25 shadow-amber-400/15'
                }`}
              >
                {message.content}
              </div>
              
              {message.type === 'user' && (
                <div className="w-8 h-8 bg-gradient-to-r from-amber-500/60 to-orange-500/60 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-400/20 border border-amber-400/30">
                  <User className="w-4 h-4 text-amber-100" />
                </div>
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-gradient-to-r from-amber-500/60 to-yellow-500/60 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-400/20 border border-amber-400/30">
                <Bot className="w-4 h-4 text-amber-100" />
              </div>
              <div className="bg-gray-900/85 backdrop-blur-md text-white p-4 rounded-2xl shadow-lg border border-amber-400/25">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-amber-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          )}
        </div>
        </ScrollArea>
      </div>

      {/* Input Area */}
      <div className="p-6 border-t border-amber-400/25">
        <div className="flex gap-3">
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="請輸入您的問題..."
            className="flex-1 min-h-[50px] max-h-[120px] resize-none bg-gray-900/70 backdrop-blur-md border-amber-400/35 text-white placeholder:text-white/50 rounded-xl focus:ring-2 focus:ring-amber-300/60 focus:border-amber-300/60 shadow-lg custom-scrollbar"
            disabled={isLoading}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="self-end bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 rounded-xl px-4 shadow-lg shadow-amber-400/30 hover:shadow-amber-400/45 border border-amber-300/40"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
