package com.example.action;

public class HelloAction {
    private String name;

    public String execute() {
        return "success";
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }
}
