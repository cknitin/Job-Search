# Static Class vs Singleton Pattern 🔄

## Quick Overview

| Aspect | Static Class | Singleton |
|--------|--------------|-----------|
| **Instance** | No instance created | One instance created |
| **Memory** | Loaded at app start | Created when first accessed |
| **Inheritance** | Cannot inherit/be inherited | Can inherit and be inherited |
| **Interface** | Cannot implement interfaces | Can implement interfaces |
| **Thread Safety** | Thread-safe by default | Requires manual thread safety |
| **Testing** | Hard to mock/test | Can be mocked/tested |
| **Polymorphism** | No polymorphism | Supports polymorphism |

---

## 1. Static Class 📌

### Definition:
A static class is a class that cannot be instantiated and contains only static members.

### ✅ Code Example:
```csharp
public static class MathHelper
{
    public static double PI = 3.14159;
    
    public static double CalculateArea(double radius)
    {
        return PI * radius * radius;
    }
    
    public static double CalculateCircumference(double radius)
    {
        return 2 * PI * radius;
    }
}

// Usage
double area = MathHelper.CalculateArea(5.0);
double circumference = MathHelper.CalculateCircumference(5.0);
```

### **Characteristics:**
- ✅ **No instantiation** - Cannot create objects
- ✅ **Compile-time binding** - Method calls resolved at compile time
- ✅ **Memory efficient** - Loaded once in memory
- ✅ **Thread-safe** - No shared instance state
- ❌ **No inheritance** - Cannot inherit from or be inherited
- ❌ **No interfaces** - Cannot implement interfaces
- ❌ **Hard to test** - Cannot mock static methods easily

---

## 2. Singleton Pattern 🎯

### Definition:
Singleton ensures a class has only one instance and provides global access to that instance.

### ✅ Code Example (Thread-Safe):
```csharp
public class DatabaseConnection
{
    private static DatabaseConnection _instance;
    private static readonly object _lock = new object();
    
    // Private constructor prevents external instantiation
    private DatabaseConnection()
    {
        ConnectionString = "Server=localhost;Database=MyDB;";
    }
    
    public static DatabaseConnection Instance
    {
        get
        {
            if (_instance == null)
            {
                lock (_lock)
                {
                    if (_instance == null)
                        _instance = new DatabaseConnection();
                }
            }
            return _instance;
        }
    }
    
    public string ConnectionString { get; private set; }
    
    public void ExecuteQuery(string query)
    {
        Console.WriteLine($"Executing: {query}");
    }
}

// Usage
DatabaseConnection db = DatabaseConnection.Instance;
db.ExecuteQuery("SELECT * FROM Users");
```

### **Modern C# Singleton (Lazy<T>):**
```csharp
public class ConfigurationManager
{
    private static readonly Lazy<ConfigurationManager> _instance = 
        new Lazy<ConfigurationManager>(() => new ConfigurationManager());
    
    private ConfigurationManager()
    {
        LoadConfiguration();
    }
    
    public static ConfigurationManager Instance => _instance.Value;
    
    public string GetSetting(string key) => $"Value for {key}";
    
    private void LoadConfiguration()
    {
        // Load config from file/database
    }
}
```

### **Characteristics:**
- ✅ **One instance** - Exactly one object in memory
- ✅ **Lazy initialization** - Created when first needed
- ✅ **Can inherit** - Can extend other classes
- ✅ **Can implement interfaces** - Supports polymorphism
- ✅ **Testable** - Can be mocked and tested
- ❌ **Thread safety complexity** - Requires careful implementation
- ❌ **Hidden dependencies** - Global state can be problematic

---

## 🔍 Detailed Comparison

### **1. Memory & Performance**

#### Static Class:
```csharp
public static class Logger
{
    static Logger() // Static constructor called once
    {
        Console.WriteLine("Logger initialized at app start");
    }
    
    public static void Log(string message)
    {
        Console.WriteLine($"[LOG]: {message}");
    }
}
```
- **Memory:** Loaded at application startup
- **Performance:** Fastest access (no instance creation)
- **Lifetime:** Lives for entire application lifetime

#### Singleton:
```csharp
public class Logger
{
    private static readonly Lazy<Logger> _instance = new(() => new Logger());
    
    private Logger()
    {
        Console.WriteLine("Logger instance created when first accessed");
    }
    
    public static Logger Instance => _instance.Value;
    
    public void Log(string message)
    {
        Console.WriteLine($"[LOG]: {message}");
    }
}
```
- **Memory:** Created on first access (lazy loading)
- **Performance:** Slight overhead for instance creation
- **Lifetime:** Lives until garbage collected (rare for singletons)

### **2. Inheritance & Polymorphism**

#### Static Class - ❌ No Inheritance:
```csharp
// This won't compile!
// public static class BaseLogger { }
// public static class FileLogger : BaseLogger { } // Error!

public static class MathOperations
{
    public static int Add(int a, int b) => a + b;
    // Cannot be overridden or inherited
}
```

#### Singleton - ✅ Supports Inheritance:
```csharp
public interface ILogger
{
    void Log(string message);
}

public abstract class BaseLogger : ILogger
{
    public abstract void Log(string message);
    
    protected void LogTimestamp()
    {
        Console.WriteLine($"Timestamp: {DateTime.Now}");
    }
}

public class FileLogger : BaseLogger
{
    private static readonly Lazy<FileLogger> _instance = new(() => new FileLogger());
    public static FileLogger Instance => _instance.Value;
    
    private FileLogger() { }
    
    public override void Log(string message)
    {
        LogTimestamp();
        // Write to file
        Console.WriteLine($"File Log: {message}");
    }
}

// Polymorphism in action
ILogger logger = FileLogger.Instance;
logger.Log("This works!");
```

### **3. Testing & Mocking**

#### Static Class - ❌ Hard to Test:
```csharp
public class OrderService
{
    public void ProcessOrder(Order order)
    {
        // Hard to mock EmailHelper.SendEmail()
        EmailHelper.SendEmail(order.CustomerEmail, "Order processed");
        
        // Tightly coupled to static class
        DatabaseHelper.Save(order);
    }
}

// Testing becomes difficult - cannot mock static methods
```

#### Singleton - ✅ Easier to Test:
```csharp
public interface IEmailService
{
    void SendEmail(string to, string message);
}

public class EmailService : IEmailService
{
    private static readonly Lazy<EmailService> _instance = new(() => new EmailService());
    public static EmailService Instance => _instance.Value;
    
    private EmailService() { }
    
    public void SendEmail(string to, string message)
    {
        // Send email implementation
    }
}

public class OrderService
{
    private readonly IEmailService _emailService;
    
    public OrderService(IEmailService emailService = null)
    {
        _emailService = emailService ?? EmailService.Instance;
    }
    
    public void ProcessOrder(Order order)
    {
        _emailService.SendEmail(order.CustomerEmail, "Order processed");
    }
}

// Easy to test with mock
var mockEmail = new Mock<IEmailService>();
var orderService = new OrderService(mockEmail.Object);
```

---

## 🎯 When to Use What?

### Use **Static Class** When:
- ✅ **Utility functions** (Math operations, string helpers)
- ✅ **No state management** needed
- ✅ **Simple operations** that don't require inheritance
- ✅ **Performance is critical** (no instance overhead)
- ✅ **Extension methods**

```csharp
public static class StringExtensions
{
    public static bool IsValidEmail(this string email)
    {
        return email.Contains("@") && email.Contains(".");
    }
}

// Usage
string email = "user@example.com";
bool isValid = email.IsValidEmail(); // Extension method
```

### Use **Singleton** When:
- ✅ **Managing shared resources** (Database connections, file handles)
- ✅ **Configuration management**
- ✅ **Caching mechanisms**
- ✅ **Need inheritance/interfaces**
- ✅ **Lazy initialization** is important
- ✅ **Testing/mocking** is required

```csharp
public class CacheManager : ICacheManager
{
    private static readonly Lazy<CacheManager> _instance = new(() => new CacheManager());
    public static CacheManager Instance => _instance.Value;
    
    private readonly Dictionary<string, object> _cache = new();
    
    private CacheManager() { }
    
    public T Get<T>(string key) where T : class
    {
        return _cache.ContainsKey(key) ? _cache[key] as T : null;
    }
    
    public void Set<T>(string key, T value) where T : class
    {
        _cache[key] = value;
    }
}
```

---

## ⚠️ Common Pitfalls & Best Practices

### **Static Class Pitfalls:**
```csharp
// ❌ Bad - Static state can cause issues
public static class UserManager
{
    private static string _currentUser; // Shared across all threads!
    
    public static void SetCurrentUser(string user)
    {
        _currentUser = user; // Not thread-safe!
    }
}

// ✅ Good - Stateless static methods
public static class PasswordHelper
{
    public static string HashPassword(string password)
    {
        // Pure function - no shared state
        return BCrypt.Net.BCrypt.HashPassword(password);
    }
}
```

### **Singleton Pitfalls:**
```csharp
// ❌ Bad - Not thread-safe
public class BadSingleton
{
    private static BadSingleton _instance;
    
    public static BadSingleton Instance
    {
        get
        {
            if (_instance == null) // Race condition!
                _instance = new BadSingleton();
            return _instance;
        }
    }
}

// ✅ Good - Thread-safe with Lazy<T>
public class GoodSingleton
{
    private static readonly Lazy<GoodSingleton> _instance = 
        new Lazy<GoodSingleton>(() => new GoodSingleton());
    
    public static GoodSingleton Instance => _instance.Value;
    
    private GoodSingleton() { }
}
```

---

## 📊 Summary Decision Matrix

| Requirement | Static Class | Singleton |
|-------------|--------------|-----------|
| **No state needed** | ✅ Perfect | ❌ Overkill |
| **Utility functions** | ✅ Perfect | ❌ Overkill |
| **Need inheritance** | ❌ Impossible | ✅ Perfect |
| **Need interfaces** | ❌ Impossible | ✅ Perfect |
| **Lazy loading** | ❌ No | ✅ Yes |
| **Unit testing** | ❌ Hard | ✅ Easy |
| **Performance** | ✅ Fastest | ⚠️ Good |
| **Memory usage** | ✅ Minimal | ⚠️ Small overhead |
| **Thread safety** | ✅ Built-in | ⚠️ Manual |

## 💡 Pro Tips:
1. **Prefer static classes** for utility functions and extension methods
2. **Use Lazy<T>** for thread-safe singleton implementation
3. **Consider dependency injection** instead of singleton for better testability
4. **Avoid singletons** if you can use dependency injection container
5. **Never mix static state** with multithreading without proper synchronization
