# KYOTO SHINKANSEN STRIKE

```mermaid
flowchart LR
    classDef tokyo fill:#2c3e50,color:#fff;
    classDef train fill:#7f8c8d,color:#fff;
    classDef kyoto fill:#c0392b,color:#fff;

    A[Hilton Odaiba<br>06:30 AM]:::tokyo -->|Yurikamome/JR| B[Tokyo Station<br>07:15 AM]:::tokyo
    B -->|Nozomi Shinkansen<br>Seat E for Mt. Fuji| C((2h 15m Transit)):::train
    C -->|Arrive 09:45 AM| D[Kyoto Station]:::kyoto
    D -->|Taxi 15 mins| E[Matsumoto Kiyoshi<br>Meeting Point 10:00 AM]:::kyoto
    E -->|Hiro - No Raw Seafood| F[Food Tour<br>Ends 1:00 PM]:::kyoto
    F -->|Taxi| G[Kiyomizu-dera / Free Time]:::kyoto
    G -->|Taxi| H[Kyoto Station<br>Buy Ekiben]:::kyoto
    H -->|Nozomi Shinkansen<br>06:00 PM| I((Return Transit)):::train
    I --> J[Tokyo Station<br>08:15 PM]:::tokyo
    J --> K[Hilton Odaiba]:::tokyo
```
