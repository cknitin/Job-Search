Perfect! 🚀 Let’s build a **real-world, end-to-end example** using **Azure Event Grid, Event Hubs, and Service Bus** (event-driven architecture) in **.NET (C#)**.

We’ll use your idea of **American Water Company** as the domain (water utility provider) — this will make it relatable, step-by-step from beginner → advanced → most complex flows.

---

# 🌊 Real-World Example: **American Water Smart Utility System**

American Water wants to build a **real-time monitoring and alerting system** for its water distribution network (pipes, sensors, billing, and customer notifications).

They need:

* **Event Grid** → For publishing **system-wide events** (pipe burst, billing cycle start, sensor offline, etc.).
* **Event Hub** → For **high-volume streaming telemetry** (IoT devices sending water flow, pressure, quality readings every second).
* **Service Bus** → For **business-critical workflows** (billing, outage notifications, customer ticketing).

We’ll integrate **Azure Functions** with **Triggers & Bindings** for handling events in C#.

---

# 🟢 Beginner Flow – Basic Alerts (Event Grid)

### Scenario:

* A **pipe sensor** detects a **pipe burst**.
* Sensor publishes event → Event Grid → Triggers an Azure Function → Sends alert.

### Steps:

1. **Sensor system** publishes event to **Event Grid Topic**.
   Example event schema:

   ```json
   {
     "id": "burst-789",
     "eventType": "Pipe.BurstDetected",
     "subject": "/pipes/zone-23",
     "data": {
       "location": "Zone-23",
       "severity": "High",
       "detectedAt": "2025-08-25T12:30:00Z"
     },
     "eventTime": "2025-08-25T12:30:00Z",
     "dataVersion": "1.0"
   }
   ```

2. **Event Grid subscription** triggers a **C# Azure Function**:

   ```csharp
   public static class PipeBurstHandler
   {
       [FunctionName("PipeBurstHandler")]
       public static void Run(
           [EventGridTrigger] EventGridEvent eventGridEvent,
           ILogger log)
       {
           var data = eventGridEvent.Data.ToString();
           log.LogInformation($"Pipe burst event received: {data}");
           
           // Call SMS/Email service (Twilio/SendGrid)
           log.LogInformation("Alert sent to maintenance team 🚨");
       }
   }
   ```

👉 **Key Concept**: Event Grid = lightweight **publish/subscribe** for system-wide notifications.

---

# 🟡 Intermediate Flow – Real-time Monitoring (Event Hub)

### Scenario:

* 10,000+ IoT sensors continuously send **water pressure & quality data**.
* Use **Event Hub** to stream → Azure Function processes in real-time.

### Steps:

1. IoT Device → **Event Hub**.

   ```csharp
   // Device SDK sending telemetry
   var producerClient = new EventHubProducerClient("<connection-string>", "<hub-name>");
   using EventDataBatch eventBatch = await producerClient.CreateBatchAsync();
   eventBatch.TryAdd(new EventData(Encoding.UTF8.GetBytes("{ \"deviceId\": \"sensor-01\", \"pressure\": 85, \"quality\": \"Good\" }")));
   await producerClient.SendAsync(eventBatch);
   ```

2. **Azure Function** with **EventHubTrigger** processes events:

   ```csharp
   public static class SensorDataProcessor
   {
       [FunctionName("SensorDataProcessor")]
       public static async Task Run(
           [EventHubTrigger("water-hub", Connection = "EventHubConnectionAppSetting")] string[] events,
           ILogger log)
       {
           foreach (var message in events)
           {
               log.LogInformation($"Telemetry: {message}");

               // Parse data
               var data = JsonConvert.DeserializeObject<SensorReading>(message);

               if (data.Pressure > 100)
               {
                   log.LogWarning("⚠️ High pressure detected! Sending to Service Bus for ticketing...");
               }
           }
       }
   }

   public class SensorReading
   {
       public string DeviceId { get; set; }
       public int Pressure { get; set; }
       public string Quality { get; set; }
   }
   ```

👉 **Key Concept**: Event Hub = **high-throughput telemetry ingestion** for IoT.

---

# 🔴 Advanced Flow – Workflows & Billing (Service Bus + Event Grid)

### Scenario:

* A **billing cycle starts** every month.
* Billing service → Event Grid → notifies multiple services.
* Some workflows (payment retries, sending receipts) require **guaranteed delivery & ordering** → Service Bus.

### Steps:

1. Billing Service publishes an event to **Event Grid**:

   ```json
   {
     "eventType": "Billing.CycleStarted",
     "subject": "/billing/monthly",
     "data": { "month": "August", "year": 2025 },
     "eventTime": "2025-08-25T00:00:00Z"
   }
   ```

2. **Event Grid** notifies:

   * **Analytics Service** (to calculate consumption).
   * **Notification Service** (to inform customers).

3. **Notification Service** puts **payment reminder messages** on **Service Bus Queue**:

   ```csharp
   public static class BillingReminderSender
   {
       [FunctionName("BillingReminderSender")]
       public static async Task Run(
           [EventGridTrigger] EventGridEvent eventGridEvent,
           [ServiceBus("billing-reminders", Connection = "ServiceBusConnectionAppSetting")] IAsyncCollector<string> messageCollector,
           ILogger log)
       {
           var data = JsonConvert.SerializeObject(eventGridEvent.Data);
           await messageCollector.AddAsync($"Reminder for billing cycle: {data}");
           log.LogInformation($"Billing reminder queued 📩");
       }
   }
   ```

4. **Another Function** consumes from Service Bus Queue to send emails/SMS:

   ```csharp
   public static class ReminderProcessor
   {
       [FunctionName("ReminderProcessor")]
       public static async Task Run(
           [ServiceBusTrigger("billing-reminders", Connection = "ServiceBusConnectionAppSetting")] string message,
           ILogger log)
       {
           log.LogInformation($"Processing billing reminder: {message}");
           // Call Email/SMS Service
       }
   }
   ```

👉 **Key Concept**:

* Event Grid = broad **fan-out notifications**.
* Service Bus = **reliable, ordered, guaranteed workflow processing**.

---

# 🔥 Most Complex Flow – End-to-End Integration

### Scenario:

* A **sensor detects contamination** in water supply.
* Steps:

  1. **Sensor** sends data → Event Hub.
  2. **Function** detects contamination → publishes Event Grid event.
  3. **Event Grid** notifies:

     * Emergency response service.
     * Customer alert service.
     * Billing (refund credits).
  4. **Service Bus Queue** ensures customer support tickets are created sequentially.
  5. **Dead-letter Queue** handles failed notifications (customer unreachable).

**Flow Diagram (words):**

```
IoT Device → Event Hub → Azure Function (contamination check) → Event Grid
→ [Emergency Service, Customer Alerts, Billing Service]
Customer Alerts → Service Bus Queue → Azure Function (send SMS/Email)
```

---

# ✅ Summary of Concepts Covered

* **Event Grid**

  * Beginner: Pipe burst alert (pub/sub).
  * Advanced: Billing fan-out events.
* **Event Hub**

  * IoT telemetry ingestion.
* **Service Bus**

  * Guaranteed processing of billing reminders & tickets.
  * Dead-letter handling.
* **Azure Functions Triggers & Bindings**

  * `EventGridTrigger`, `EventHubTrigger`, `ServiceBusTrigger`.
  * Output bindings (`IAsyncCollector<T>`).

---


