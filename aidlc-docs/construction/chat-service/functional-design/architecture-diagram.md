# アーキテクチャ図

## システム全体構成

```mermaid
graph TB
    subgraph Frontend["フロントエンド (React + TypeScript)"]
        EU[エンドユーザ画面<br/>EndUserInquiry]
        OL[オペレータログイン画面<br/>OperatorLogin]
        IL[問い合わせ一覧画面<br/>InquiryList]
        ID[問い合わせ詳細画面<br/>InquiryDetail]
        SB[サマリーボード<br/>SummaryBoard]
        OA[オペレータ追加<br/>OperatorAdd]
        OLS[オペレータ一覧<br/>OperatorList]
        AP[AuthProvider]
        UC[useChat Hook]
        UB[useBotChat Hook]
    end

    subgraph Backend["バックエンド (FastAPI + Python)"]
        subgraph Routers["Router層"]
            AR[auth_router]
            CR[chat_router]
            IR[inquiry_router]
            OR[operator_router]
            WR[wait_time_router]
            SR[summary_router]
            CW[chat_ws]
        end
        subgraph Services["Service層"]
            AS[AuthService]
            BS[BotService]
            IS[InquiryService]
            OS[OperatorService]
            WS[WaitTimeService]
            SS[SummaryService]
            CS[ChatService]
        end
        subgraph Repositories["Repository層"]
            ARE[AuthRepository]
            BRE[BotRepository]
            IRE[InquiryRepository]
            ORE[OperatorRepository]
            SRE[SummaryRepository]
            CRE[ChatRepository]
        end
        CM[ConnectionManager<br/>インメモリ]
        QD[questions.py<br/>BOT質問定義]
        MW[auth_middleware]
    end

    subgraph Database["データベース (SQLite)"]
        OT[(operators)]
        ST[(sessions)]
        IT[(inquiries)]
        MT[(messages)]
    end

    WT -->|HTTP GET| WR
    EU -->|HTTP POST| CR
    EU -->|WebSocket| CW
    ID -->|WebSocket| CW
    OL -->|HTTP POST| AR
    IL -->|HTTP GET| IR
    ID -->|HTTP GET| IR
    SB -->|HTTP GET| SR
    OA -->|HTTP POST| OR
    OLS -->|HTTP GET/DELETE| OR

    AR --> AS
    AR --> OS
    CR --> BS
    IR --> IS
    IR --> MW
    OR --> OS
    WR --> WS
    SR --> SS
    CW --> CS
    CW --> MW

    AS --> ARE
    BS --> BRE
    BS --> IRE
    BS --> QD
    BS --> CM
    IS --> IRE
    OS --> ORE
    WS --> IRE
    WS --> ARE
    SS --> SRE
    CS --> CRE
    CS --> IRE
    CS --> CM

    ARE --> OT
    ARE --> ST
    ORE --> OT
    IRE --> IT
    IRE --> MT
    BRE --> IT
    BRE --> MT
    CRE --> MT
    SRE --> IT
    SRE --> MT

    style Frontend fill:#BBDEFB,stroke:#1565C0,stroke-width:2px
    style Backend fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px
    style Database fill:#FFF9C4,stroke:#F57F17,stroke-width:2px
    style Routers fill:#E1F5FE,stroke:#0288D1,stroke-width:1px
    style Services fill:#E8F5E9,stroke:#388E3C,stroke-width:1px
    style Repositories fill:#F1F8E9,stroke:#558B2F,stroke-width:1px
```

## バックエンド レイヤー構成

```mermaid
graph LR
    subgraph Layer1["Router / WebSocket Handler"]
        R1[auth_router]
        R2[chat_router]
        R3[inquiry_router]
        R4[operator_router]
        R5[wait_time_router]
        R6[summary_router]
        R7[chat_ws]
    end

    subgraph Layer2["Service"]
        S1[AuthService]
        S2[BotService]
        S3[InquiryService]
        S4[OperatorService]
        S5[WaitTimeService]
        S6[SummaryService]
        S7[ChatService]
    end

    subgraph Layer3["Repository"]
        D1[AuthRepository]
        D2[BotRepository]
        D3[InquiryRepository]
        D4[OperatorRepository]
        D5[SummaryRepository]
        D6[ChatRepository]
    end

    subgraph Infra["インフラ"]
        CM[ConnectionManager]
        QD[questions.py]
        DB[(SQLite)]
    end

    R1 --> S1
    R1 --> S4
    R2 --> S2
    R3 --> S3
    R4 --> S4
    R5 --> S5
    R6 --> S6
    R7 --> S7

    S1 --> D1
    S2 --> D2
    S2 --> D3
    S2 --> QD
    S2 --> CM
    S3 --> D3
    S4 --> D4
    S5 --> D3
    S5 --> D1
    S6 --> D5
    S7 --> D6
    S7 --> D3
    S7 --> CM

    D1 --> DB
    D2 --> DB
    D3 --> DB
    D4 --> DB
    D5 --> DB
    D6 --> DB

    style Layer1 fill:#E3F2FD,stroke:#1976D2,stroke-width:1px
    style Layer2 fill:#E8F5E9,stroke:#388E3C,stroke-width:1px
    style Layer3 fill:#FFF3E0,stroke:#F57C00,stroke-width:1px
    style Infra fill:#F3E5F5,stroke:#7B1FA2,stroke-width:1px
```

## フロントエンド コンポーネント構成

```mermaid
graph TB
    App[App]
    App --> AuthProv[AuthProvider]

    AuthProv --> Route1["/ : EndUserInquiry"]
    AuthProv --> Route2["/operator/login : OperatorLogin"]
    AuthProv --> Protected[ProtectedRoute]

    Protected --> Nav[OperatorNav]
    Protected --> Route3["/operator/inquiries : InquiryList"]
    Protected --> Route4["/operator/inquiries/:id : InquiryDetail"]
    Protected --> Route5["/operator/users : OperatorList"]
    Protected --> Route6["/operator/users/add : OperatorAdd"]
    Protected --> Route7["/operator/summary-board : SummaryBoard"]

    Route1 --> WTC[WaitTimeChart]
    Route1 --> CW1[ChatWindow]
    Route1 --> BQI[BotQuestionInput]
    Route1 --> MI1[MessageInput]
    Route1 --> CS1[ConnectionStatus]
    Route1 --> EB[EndButton]
    BQI --> CQ[ChoiceQuestion]
    BQI --> SQ[SizeQuestion]

    Route3 --> IT[InquiryTable]
    IT --> IR[InquiryRow]
    IR --> SB[StatusBadge]
    IR --> AB[AssignButton]

    Route4 --> II[InquiryInfo]
    Route4 --> CW2[ChatWindow]
    Route4 --> MI2[MessageInput]

    Route7 --> HSC[HourlySessionChart]
    Route7 --> HRC[HourlyResponseTimeChart]

    style App fill:#CE93D8,stroke:#6A1B9A,stroke-width:2px
    style AuthProv fill:#B39DDB,stroke:#4527A0,stroke-width:1px
    style Protected fill:#FFCC80,stroke:#EF6C00,stroke-width:1px
```
