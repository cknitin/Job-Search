# SOLID Principles Cheat Sheet 🚀

## Quick Memory Aid: **"SOLID"**
- **S** - Single Responsibility Principle
- **O** - Open/Closed Principle  
- **L** - Liskov Substitution Principle
- **I** - Interface Segregation Principle
- **D** - Dependency Inversion Principle

---

## 1. Single Responsibility Principle (SRP) 📝
### **"One Class, One Job"**

**Official Definition:** A class should have only one reason to change, meaning that a class should have only one job or responsibility.

**Rule:** A class should have only one reason to change.

### ❌ Bad Example:
```csharp
public class Employee
{
    public void SaveEmployee() { /* Save to database */ }
    public void SendEmail() { /* Send email notification */ }
    public void GenerateReport() { /* Generate PDF report */ }
}
// Problem: 3 different reasons to change this class!
```

### ✅ Good Example:
```csharp
public class Employee
{
    public string Name { get; set; }
    public decimal Salary { get; set; }
}

public class EmployeeRepository
{
    public void SaveEmployee(Employee emp) { /* Save logic */ }
}

public class EmailService
{
    public void SendEmail(string message) { /* Email logic */ }
}

public class ReportGenerator
{
    public void GenerateReport(Employee emp) { /* Report logic */ }
}
```

**Memory Tip:** "Single = Solo = One job per class"

---

## 2. Open/Closed Principle (OCP) 🔓🔒
### **"Open for Extension, Closed for Modification"**

**Official Definition:** Software entities (classes, modules, functions, etc.) should be open for extension but closed for modification. This means you should be able to add new functionality without changing existing code.

**Rule:** Classes should be open for extension but closed for modification.

### ❌ Bad Example:
```csharp
public class AreaCalculator
{
    public double CalculateArea(object shape)
    {
        if (shape is Rectangle rect)
            return rect.Width * rect.Height;
        else if (shape is Circle circle)
            return Math.PI * circle.Radius * circle.Radius;
        // Need to modify this method for new shapes!
        return 0;
    }
}
```

### ✅ Good Example:
```csharp
public abstract class Shape
{
    public abstract double CalculateArea();
}

public class Rectangle : Shape
{
    public double Width { get; set; }
    public double Height { get; set; }
    
    public override double CalculateArea() => Width * Height;
}

public class Circle : Shape
{
    public double Radius { get; set; }
    
    public override double CalculateArea() => Math.PI * Radius * Radius;
}

public class AreaCalculator
{
    public double CalculateArea(Shape shape) => shape.CalculateArea();
    // No need to modify for new shapes!
}
```

**Memory Tip:** "Open door for new features, Closed door for changes"

---

## 3. Liskov Substitution Principle (LSP) 🔄
### **"Subclasses Must Be Substitutable"**

**Official Definition:** Objects of a superclass should be replaceable with objects of its subclasses without breaking the application. In other words, if S is a subtype of T, then objects of type T may be replaced with objects of type S without altering any of the desirable properties of the program.

**Rule:** Objects of a superclass should be replaceable with objects of a subclass without breaking functionality.

### ❌ Bad Example:
```csharp
public class Bird
{
    public virtual void Fly() => Console.WriteLine("Flying...");
}

public class Penguin : Bird
{
    public override void Fly() => throw new Exception("Can't fly!");
    // Breaks LSP - penguin can't substitute bird behavior
}
```

### ✅ Good Example:
```csharp
public abstract class Bird
{
    public abstract void Move();
}

public class FlyingBird : Bird
{
    public override void Move() => Console.WriteLine("Flying...");
}

public class SwimmingBird : Bird
{
    public override void Move() => Console.WriteLine("Swimming...");
}

public class Eagle : FlyingBird { }
public class Penguin : SwimmingBird { }
```

**Memory Tip:** "Lisa (Liskov) can substitute any family member in photos"

---

## 4. Interface Segregation Principle (ISP) ✂️
### **"Many Small Interfaces > One Big Interface"**

**Official Definition:** No client should be forced to depend on methods it does not use. This principle suggests that it's better to have many specific interfaces rather than one general-purpose interface.

**Rule:** Clients should not be forced to depend on interfaces they don't use.

### ❌ Bad Example:
```csharp
public interface IWorker
{
    void Work();
    void Eat();
    void Sleep();
}

public class Robot : IWorker
{
    public void Work() => Console.WriteLine("Working...");
    public void Eat() => throw new NotImplementedException(); // Robot doesn't eat!
    public void Sleep() => throw new NotImplementedException(); // Robot doesn't sleep!
}
```

### ✅ Good Example:
```csharp
public interface IWorkable
{
    void Work();
}

public interface IFeedable
{
    void Eat();
}

public interface ISleepable
{
    void Sleep();
}

public class Human : IWorkable, IFeedable, ISleepable
{
    public void Work() => Console.WriteLine("Working...");
    public void Eat() => Console.WriteLine("Eating...");
    public void Sleep() => Console.WriteLine("Sleeping...");
}

public class Robot : IWorkable
{
    public void Work() => Console.WriteLine("Working...");
    // Only implements what it needs!
}
```

**Memory Tip:** "Interface Separation = Split interfaces like pizza slices"

---

## 5. Dependency Inversion Principle (DIP) 🔃
### **"Depend on Abstractions, Not Concretions"**

**Official Definition:** High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details. Details should depend on abstractions.

**Rule:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

### ❌ Bad Example:
```csharp
public class EmailService
{
    public void SendEmail(string message) { /* Send email */ }
}

public class NotificationService
{
    private EmailService emailService = new EmailService(); // Tight coupling!
    
    public void SendNotification(string message)
    {
        emailService.SendEmail(message);
    }
}
```

### ✅ Good Example:
```csharp
public interface IMessageService
{
    void SendMessage(string message);
}

public class EmailService : IMessageService
{
    public void SendMessage(string message) => Console.WriteLine($"Email: {message}");
}

public class SMSService : IMessageService
{
    public void SendMessage(string message) => Console.WriteLine($"SMS: {message}");
}

public class NotificationService
{
    private readonly IMessageService messageService;
    
    public NotificationService(IMessageService messageService)
    {
        this.messageService = messageService; // Dependency injection!
    }
    
    public void SendNotification(string message)
    {
        messageService.SendMessage(message);
    }
}
```

**Memory Tip:** "Depend on Interface (abstract), not Implementation (concrete)"

---

## 🎯 Quick Reference Summary

| Principle | Simple Rule | Memory Hook |
|-----------|-------------|-------------|
| **SRP** | One class, one job | Single = Solo |
| **OCP** | Extend, don't modify | Open door, closed door |
| **LSP** | Child can replace parent | Lisa substitutes family |
| **ISP** | Small focused interfaces | Split like pizza slices |
| **DIP** | Depend on abstractions | Interface over Implementation |

## 🏆 Benefits of Following SOLID:
- ✅ **Maintainable** code
- ✅ **Testable** components  
- ✅ **Flexible** architecture
- ✅ **Reusable** modules
- ✅ **Scalable** applications

## 💡 Pro Tip:
Start with **SRP** and **DIP** - they provide the biggest impact with minimal effort!
